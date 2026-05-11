# app.py — Flask-сервер CodeDreamers
import sys
import os
import json
import queue
import threading

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Инициализируем БД и seed до старта Flask
if not os.path.exists("codedreamers.db"):
    from config import ConfigManager
    from database import DatabaseManager
    ConfigManager()
    DatabaseManager()
    from seed import seed
    seed()

from flask import Flask, jsonify, request, send_from_directory, Response, stream_with_context
from patterns.proxy.course_service_proxy import CourseServiceProxy
from services.recommendation_service import recommend_courses
from patterns.factory.abstract_factory import get_package_factory
from patterns.template.lesson_process import CourseProcessFactory
from services.course_facade import CourseFacade
from patterns.observer.event_bus import EventBus, SystemEvent, NotificationEvent
from database import DatabaseManager

app = Flask(__name__, static_folder="static", static_url_path="")

# ── SSE: черга подій для пушів ────────────────────────────────────────────

_sse_clients: list[queue.Queue] = []
_sse_lock = threading.Lock()


def _broadcast(event: SystemEvent) -> None:
    """Надсилає подію всім SSE-клієнтам."""
    data = json.dumps({
        "type": event.event_type,
        "timestamp": event.timestamp,
        **{k: v for k, v in event.__dict__.items() if k != "timestamp"},
    })
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(data)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


# Підписуємо broadcast на всі події
for _evt_cls in [
    "EnrollEvent", "UnenrollEvent", "CompleteEvent",
    "StateChangedEvent", "LessonAddedEvent", "NotificationEvent", "LessonCompletedEvent",
]:
    import importlib
    _mod = importlib.import_module("patterns.observer.event_bus")
    _cls = getattr(_mod, _evt_cls, None)
    if _cls:
        EventBus().subscribe(_cls, _broadcast)


def get_proxy() -> CourseServiceProxy:
    role = request.headers.get("X-Role", "student").lower()
    return CourseServiceProxy(role)


# ── Фронтенд ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── SSE: push-сповіщення (Observer -> клієнт) ────────────────────────────

@app.route("/api/events")
def api_events():
    """GET /api/events — SSE stream для push-сповіщень."""
    q = queue.Queue(maxsize=50)
    with _sse_lock:
        _sse_clients.append(q)

    def generate():
        yield "data: {\"type\":\"connected\"}\n\n"
        try:
            while True:
                try:
                    data = q.get(timeout=30)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
        except GeneratorExit:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── API: отмена курсов ─────────────────
from patterns.command.system_commands import (
    CreateCourseCommand,
    AddLessonCommand,
    ChangeStateCommand,
    SendNotificationCommand,
    CreateModuleCommand,
    AddDisciplineToModuleCommand,
)

from patterns.command.course_commands import CommandHistory as CmdHistory

# Временная глобальная история (в реальности — лучше по сессиям)
command_history = CmdHistory()

from patterns.command.course_commands import DeleteCourseCommand

@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def api_delete_course(course_id):
    try:
        cmd = DeleteCourseCommand(course_id)
        result = command_history.execute(cmd)
        return jsonify({"result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/command/execute", methods=["POST"])
def api_execute_command():
    data = request.get_json()
    cmd_type = data.get("type")
    params = data.get("params", {})
    from models.course import Course
    try:
        if cmd_type == "CreateCourse":
            cmd = CreateCourseCommand(
                title=params["title"],
                description=params["description"],
                base_price=float(params["price"]),
                category=params["category"],
                tags=params.get("tags", []),
            )
            result = command_history.execute(cmd)
            # Возвращаем информацию о созданном курсе
            created_course = cmd.result
            return jsonify({
                "result": result,
                "course_id": created_course.id if created_course else None,
                "title": created_course.title if created_course else None,
                "difficulty_level": created_course.difficulty_level if created_course else "basic"
            })
        elif cmd_type == "AddLesson":
            # Загружаем курс из БД
            db = DatabaseManager()
            course_row = db.fetchone("SELECT * FROM courses WHERE id = ?", (params["course_id"],))
            if not course_row:
                return jsonify({"error": "Course not found"}), 404
            
            course = Course(
                id=course_row["id"],
                title=course_row["title"],
                description=course_row["description"],
                price=course_row["price"],
                difficulty_level=course_row["difficulty_level"]
            )
            cmd = AddLessonCommand(
                course=course,
                title=params["title"],
                content=params["content"],
                order_num=int(params["order_num"]),
                module_id=params.get("module_id")
            )
            result = command_history.execute(cmd)
            return jsonify({"result": result})
        else:
            return jsonify({"error": "Unknown command"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/command/undo", methods=["POST"])
def api_undo_command():
    try:
        result = command_history.undo_last()
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── API: курси ────────────────────────────────────────────────────────────

@app.route("/api/courses")
def api_courses():
    try:
        return jsonify(get_proxy().get_courses())
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@app.route("/api/courses/<int:course_id>")
def api_course(course_id):
    try:
        course = get_proxy().get_course(course_id)
        if not course:
            return jsonify({"error": "Not found"}), 404
        # Додаємо стан та теги
        db = DatabaseManager()
        row = db.fetchone("SELECT state FROM courses WHERE id = ?", (course_id,))
        tags = [r["tag"] for r in db.fetchall(
            "SELECT tag FROM course_tags WHERE course_id = ?", (course_id,)
        )]
        course["state"] = row["state"] if row and row["state"] else "new"
        course["tags"] = tags
        return jsonify(course)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@app.route("/api/courses", methods=["POST"])
def api_create_course():
    """POST /api/courses — створити курс (Facade + Factory + State)."""
    data = request.get_json() or {}
    required = ["title", "description", "price", "category"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Required: {required}"}), 400
    try:
        result = CourseFacade().create_course(
            title=data["title"],
            description=data["description"],
            price=float(data["price"]),
            category=data["category"],
            tags=data.get("tags", []),
        )
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── API: стан курсу (State Machine) ──────────────────────────────────────

@app.route("/api/courses/<int:course_id>/state")
def api_course_state(course_id):
    """GET /api/courses/<id>/state — поточний стан курсу."""
    return jsonify(CourseFacade().get_state(course_id))


@app.route("/api/courses/<int:course_id>/state", methods=["POST"])
def api_course_state_transition(course_id):
    """
    POST /api/courses/<id>/state
    Body: {"action": "assign_mentor"|"assign_user"|"start_progress"|"complete"}
    """
    data = request.get_json() or {}
    action = data.get("action")
    if not action:
        return jsonify({"error": "Required: action"}), 400
    try:
        # Используем Command для возможности отмены
        cmd = ChangeStateCommand(course_id, action)
        result = command_history.execute(cmd)
        
        # Получаем новое состояние
        db = DatabaseManager()
        row = db.fetchone("SELECT state FROM courses WHERE id = ?", (course_id,))
        current_state = row["state"] if row else "new"
        
        return jsonify({
            "message": result,
            "state": current_state
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── API: уроки ────────────────────────────────────────────────────────────

@app.route("/api/courses/<int:course_id>/lessons")
def api_lessons(course_id):
    try:
        return jsonify(get_proxy().get_lessons(course_id))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@app.route("/api/courses/<int:course_id>/lessons", methods=["POST"])
def api_add_lesson(course_id):
    """POST /api/courses/<id>/lessons — додати урок (Facade + Command)."""
    data = request.get_json() or {}
    if not all(k in data for k in ["title", "content", "order_num"]):
        return jsonify({"error": "Required: title, content, order_num"}), 400
    try:
        result = CourseFacade().add_lesson(
            course_id,
            data["title"], data["content"], int(data["order_num"])
        )
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── API: теги ─────────────────────────────────────────────────────────────

@app.route("/api/courses/<int:course_id>/tags", methods=["POST"])
def api_set_tags(course_id):
    """POST /api/courses/<id>/tags  Body: {"tags": ["python","web"]}"""
    data = request.get_json() or {}
    tags = data.get("tags", [])
    return jsonify({"tags": CourseFacade().set_tags(course_id, tags)})


@app.route("/api/tags/suggest", methods=["POST"])
def api_suggest_tags():
    """POST /api/tags/suggest  Body: {"description": "..."}"""
    data = request.get_json() or {}
    desc = data.get("description", "")
    return jsonify({"tags": CourseFacade().suggest_tags(desc)})


# ── API: AI ───────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """POST /api/chat  Body: {"message": "..."}"""
    import g4f
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Required: message"}), 400

    # Получаем все курсы
    try:
        courses = get_proxy().get_courses()
    except Exception as e:
        courses = []
        print("Warning: Cannot load courses for AI context:", e)

    # Формируем краткий контекст
    courses_context = "\n".join([
        f"- {c['title']} ({c.get('category', 'N/A')}, уровень: {c.get('level', 'N/A')}): {c.get('description', '')[:150]}..."
        for c in courses
    ]) if courses else "Нет доступных курсов."

    # Системный промпт с контекстом
    system_prompt = (
        "Ты — помощник онлайн-школы CodeDreamers. Ниже список доступных курсов. "
        "Если пользователь спрашивает про обучение, выбор курса, карьеру или технологии — "
        "рекомендуй подходящий курс из списка. Объясни выбор кратко и дружелюбно.\n\n"
        "Если вопрос не связан с курсами — отвечай как обычно.\n\n"
        "Доступные курсы:\n"
        f"{courses_context}"
    )

    try:
        response = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
        )
        return jsonify({"reply": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/courses/<int:course_id>/ask", methods=["POST"])
def api_ask_ai(course_id):
    """POST /api/courses/<id>/ask  Body: {"question": "..."}"""
    data = request.get_json() or {}
    #question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Required: question"}), 400

    # Получаем все курсы
    try:
        courses = get_proxy().get_courses()
    except:
        courses = []

    # Формируем контекст с информацией о курсах
    courses_context = "\n".join([
        f"- {c['title']} ({c.get('category', 'N/A')}): {c.get('description', '')[:100]}..."
        for c in courses[:10]  # Ограничиваем, чтобы не перегружать токены
    ])

    question = 'назови рандомный курс из этого списка \n f"{courses_context} \n'
    # system_prompt = (
    #     "Ты — помощник онлайн-школы CodeDreamers. Ниже представлены доступные курсы. "
    #     "Если пользователь спрашивает, какой курс выбрать, или что поучить, "
    #     "рекомендуй один или несколько подходящих курсов ТОЛЬКО ИЗ НИЖЕ ПРЕДСТАВЛЕННОГО СПИСКА. "
    #     "Объясни выбор кратко и дружелюбно.\n\n"
    #     "Доступные курсы:\n"
    #     f"{courses_context}\n\n"
    #     "Отвечай только на основе этой информации."
    # )

    import g4f
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=[
                #{"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
        )
        return jsonify({"question": question, "answer": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/quiz", methods=["POST"])
def api_generate_quiz():
    """POST /api/quiz  Body: {"topic": "...", "count": 3}"""
    data = request.get_json() or {}
    topic = data.get("topic", "programming")
    count = int(data.get("count", 3))
    return jsonify(CourseFacade().generate_quiz(topic, count))


# ── API: програма (Composite) ─────────────────────────────────────────────

@app.route("/api/courses/<int:course_id>/program")
def api_program(course_id):
    try:
        return jsonify(get_proxy().get_program(course_id))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ── API: пакети курсу (Abstract Factory + Decorator) ─────────────────────

@app.route("/api/courses/<int:course_id>/package")
def api_course_package(course_id):
    """GET /api/courses/<id>/package?tier=basic|standard|premium"""
    tier = request.args.get("tier", "basic")
    try:
        return jsonify(CourseFacade().get_package(course_id, tier))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── API: навчальний процес (Template Method / BPMN) ───────────────────────

@app.route("/api/users/<int:user_id>/courses/<int:course_id>/process", methods=["POST"])
def api_lesson_process(user_id, course_id):
    return jsonify(CourseProcessFactory.run(user_id, course_id))


# ── API: запись на курс / прохождение ────────────────────────────────────

from patterns.command.course_commands import EnrollCommand, UnenrollCommand, CompleteCourseCommand
from services.progress_service import ProgressService

@app.route("/api/users/<int:user_id>/courses/<int:course_id>/enroll", methods=["POST"])
def api_enroll(user_id, course_id):
    db = DatabaseManager()
    user_row = db.fetchone("SELECT * FROM users WHERE id=?", (user_id,))
    course_row = db.fetchone("SELECT * FROM courses WHERE id=?", (course_id,))
    if not user_row or not course_row:
        return jsonify({"error": "User or course not found"}), 404
    from models.user import User
    from models.course import Course
    user = User(user_row["id"], user_row["name"], user_row["email"], user_row["role"])
    course = Course(course_row["id"], course_row["title"], course_row["description"],
                    course_row["price"], course_row["difficulty_level"])
    cmd = EnrollCommand(user, course)
    result = command_history.execute(cmd)
    return jsonify({"result": result})


@app.route("/api/users/<int:user_id>/courses/<int:course_id>/unenroll", methods=["POST"])
def api_unenroll(user_id, course_id):
    db = DatabaseManager()
    user_row = db.fetchone("SELECT * FROM users WHERE id=?", (user_id,))
    course_row = db.fetchone("SELECT * FROM courses WHERE id=?", (course_id,))
    if not user_row or not course_row:
        return jsonify({"error": "User or course not found"}), 404
    from models.user import User
    from models.course import Course
    user = User(user_row["id"], user_row["name"], user_row["email"], user_row["role"])
    course = Course(course_row["id"], course_row["title"], course_row["description"],
                    course_row["price"], course_row["difficulty_level"])
    cmd = UnenrollCommand(user, course)
    result = command_history.execute(cmd)
    return jsonify({"result": result})


@app.route("/api/users/<int:user_id>/courses/<int:course_id>/progress")
def api_course_progress(user_id, course_id):
    return jsonify(ProgressService().get_course_progress(user_id, course_id))


@app.route("/api/users/<int:user_id>/lessons/<int:lesson_id>/complete", methods=["POST"])
def api_complete_lesson(user_id, lesson_id):
    result = ProgressService().complete_lesson(user_id, lesson_id)
    return jsonify({"result": result})


# ── API: записи студента ──────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>/enrollments")
def api_enrollments(user_id):
    try:
        enrollments = get_proxy().get_enrollments(user_id)
        # Добавляем информацию о состоянии курса
        db = DatabaseManager()
        for enrollment in enrollments:
            course_id = enrollment.get('course_id')
            if course_id:
                # Получаем состояние курса
                state_row = db.fetchone("SELECT state FROM courses WHERE id = ?", (course_id,))
                state_name = state_row["state"] if state_row and state_row["state"] else "new"
                
                # Получаем информацию о состоянии для отображения
                from patterns.state.course_state import _STATE_MAP
                state_obj = _STATE_MAP.get(state_name, _STATE_MAP["new"])
                
                enrollment['state'] = {
                    'name': state_name,
                    'display_name': state_obj.display_name,
                    'color': state_obj.color
                }
        
        return jsonify(enrollments)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ── API: рекомендації (Content-Based Filtering) ───────────────────────────

@app.route("/api/users/<int:user_id>/recommendations")
def api_recommendations(user_id):
    top_n = request.args.get("top_n", 3, type=int)
    return jsonify(recommend_courses(user_id, top_n))


# ── API: вектор рекомендацій (мат. модель для Canvas) ────────────────────

@app.route("/api/users/<int:user_id>/vector")
def api_recommendation_vector(user_id):
    """GET /api/users/<id>/vector — дані для відрисовки вектора на Canvas."""
    return jsonify(CourseFacade().get_recommendation_vector(user_id))


# ── API: аналітика (Adapter) ──────────────────────────────────────────────

@app.route("/api/analytics/revenue")
def api_revenue():
    try:
        get_proxy()._check("analytics")
        return jsonify(CourseFacade().revenue_report())
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@app.route("/api/analytics/top-students")
def api_top_students():
    try:
        get_proxy()._check("analytics")
        top_n = request.args.get("top_n", 3, type=int)
        return jsonify(CourseFacade().top_students(top_n))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ── API: користувачі (mentor/admin) ──────────────────────────────────────

@app.route("/api/users")
def api_users():
    try:
        return jsonify(get_proxy().get_users())
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ── API: сповіщення (admin -> students) ─────────────────────────────────

@app.route("/api/notify", methods=["POST"])
def api_notify():
    """POST /api/notify  Body: {"message": "...", "recipient": "all"}"""
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Required: message"}), 400
    recipient = data.get("recipient", "all")
    
    # Используем Command для возможности отмены
    cmd = SendNotificationCommand(message, recipient)
    result = command_history.execute(cmd)
    
    return jsonify({"ok": True, "recipient": recipient, "message": message, "result": result})


# ── API: лог подій (EventBus) ─────────────────────────────────────────────

@app.route("/api/events/log")
def api_events_log():
    """GET /api/events/log — останні події системи."""
    log = EventBus().get_log()[-50:]
    return jsonify([{
        "type": e.event_type,
        "timestamp": e.timestamp,
        **{k: v for k, v in e.__dict__.items() if k != "timestamp"},
    } for e in log])


# ── API: модули курса ───────────────────────────────────────────────────────────────

@app.route("/api/courses/<int:course_id>/modules")
def api_get_modules(course_id):
    db = DatabaseManager()
    modules = db.fetchall(
        "SELECT m.id, m.title, m.order_num, m.teacher_id, u.name as teacher_name "
        "FROM modules m LEFT JOIN users u ON m.teacher_id = u.id "
        "WHERE m.course_id = ? ORDER BY m.order_num",
        (course_id,)
    )
    result = []
    for mod in modules:
        discs = db.fetchall(
            "SELECT d.id, d.title, d.description, md.order_num "
            "FROM module_disciplines md JOIN disciplines d ON md.discipline_id = d.id "
            "WHERE md.module_id = ? ORDER BY md.order_num",
            (mod["id"],)
        )
        result.append({
            "id": mod["id"], "title": mod["title"],
            "order_num": mod["order_num"],
            "teacher_id": mod["teacher_id"],
            "teacher_name": mod["teacher_name"],
            "disciplines": [dict(d) for d in discs],
        })
    return jsonify(result)


@app.route("/api/courses/<int:course_id>/modules", methods=["POST"])
def api_create_module(course_id):
    data = request.get_json() or {}
    if not data.get("title"):
        return jsonify({"error": "Required: title"}), 400
    try:
        cmd = CreateModuleCommand(
            course_id=course_id,
            title=data["title"],
            order_num=data.get("order_num", 1),
            teacher_id=data.get("teacher_id")
        )
        result = command_history.execute(cmd)
        module = cmd.result
        return jsonify({"result": result, "module": module}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/modules/<int:module_id>/disciplines", methods=["POST"])
def api_add_discipline_to_module(module_id):
    data = request.get_json() or {}
    if not data.get("discipline_id"):
        return jsonify({"error": "Required: discipline_id"}), 400
    try:
        cmd = AddDisciplineToModuleCommand(
            module_id=module_id,
            discipline_id=data["discipline_id"],
            order_num=data.get("order_num", 1)
        )
        result = command_history.execute(cmd)
        return jsonify({"result": result}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/modules/<int:module_id>/disciplines/<int:discipline_id>", methods=["DELETE"])
def api_remove_discipline_from_module(module_id, discipline_id):
    try:
        cmd = AddDisciplineToModuleCommand(module_id, discipline_id)
        # Для удаления создаем команду с уже существующей связью
        cmd._link_id = module_id * 1000 + discipline_id  # заглушка
        result = command_history.undo_last()
        return jsonify({"result": result, "ok": True})
    except Exception as e:
        DatabaseManager().execute(
            "DELETE FROM module_disciplines WHERE module_id=? AND discipline_id=?",
            (module_id, discipline_id)
        )
        return jsonify({"ok": True})


# ── API: дисциплины ───────────────────────────────────────────────────────────────

@app.route("/api/disciplines")
def api_get_disciplines():
    db = DatabaseManager()
    discs = db.fetchall("SELECT id, title, description FROM disciplines ORDER BY title")
    result = []
    for d in discs:
        lessons = db.fetchall("SELECT id, title, order_num FROM lessons WHERE discipline_id = ? ORDER BY order_num", (d["id"],))
        usages = db.fetchall(
            "SELECT m.id as module_id, m.title as module_title, "
            "c.id as course_id, c.title as course_title "
            "FROM module_disciplines md "
            "JOIN modules m ON md.module_id = m.id "
            "JOIN courses c ON m.course_id = c.id "
            "WHERE md.discipline_id = ?",
            (d["id"],)
        )
        result.append({
            "id": d["id"], "title": d["title"], "description": d["description"],
            "lessons": [dict(l) for l in lessons],
            "used_in": [dict(u) for u in usages],
        })
    return jsonify(result)


@app.route("/api/disciplines/<int:discipline_id>")
def api_get_discipline(discipline_id):
    db = DatabaseManager()
    d = db.fetchone("SELECT * FROM disciplines WHERE id = ?", (discipline_id,))
    if not d:
        return jsonify({"error": "Not found"}), 404
    lessons = db.fetchall("SELECT * FROM lessons WHERE discipline_id = ? ORDER BY order_num", (discipline_id,))
    return jsonify({
        "id": d["id"], "title": d["title"], "description": d["description"], "content": d["content"],
        "lessons": [dict(l) for l in lessons]
    })


@app.route("/api/disciplines", methods=["POST"])
def api_create_discipline():
    data = request.get_json() or {}
    if not data.get("title"):
        return jsonify({"error": "Required: title"}), 400
    cursor = DatabaseManager().execute(
        "INSERT INTO disciplines (title, description, content) VALUES (?, ?, ?)",
        (data["title"], data.get("description", ""), data.get("content", ""))
    )
    return jsonify({"id": cursor.lastrowid, "title": data["title"]}), 201


@app.route("/api/disciplines/<int:discipline_id>", methods=["PUT"])
def api_update_discipline(discipline_id):
    data = request.get_json() or {}
    DatabaseManager().execute(
        "UPDATE disciplines SET title = ?, description = ?, content = ? WHERE id = ?",
        (data.get("title", ""), data.get("description", ""), data.get("content", ""), discipline_id)
    )
    return jsonify({"ok": True})


@app.route("/api/disciplines/<int:discipline_id>", methods=["DELETE"])
def api_delete_discipline(discipline_id):
    db = DatabaseManager()
    db.execute("DELETE FROM module_disciplines WHERE discipline_id = ?", (discipline_id,))
    db.execute("DELETE FROM lessons WHERE discipline_id = ?", (discipline_id,))
    db.execute("DELETE FROM disciplines WHERE id = ?", (discipline_id,))
    return jsonify({"ok": True})


@app.route("/api/disciplines/<int:discipline_id>/lessons", methods=["POST"])
def api_add_discipline_lesson(discipline_id):
    data = request.get_json() or {}
    if not data.get("title"):
        return jsonify({"error": "Required: title"}), 400
    cursor = DatabaseManager().execute(
        "INSERT INTO lessons (discipline_id, title, content, order_num, course_id) VALUES (?, ?, ?, ?, 0)",
        (discipline_id, data["title"], data.get("content", ""), data.get("order_num", 1))
    )
    return jsonify({"id": cursor.lastrowid, "title": data["title"]}), 201


@app.route("/api/lessons/<int:lesson_id>", methods=["PUT"])
def api_update_lesson(lesson_id):
    data = request.get_json() or {}
    DatabaseManager().execute(
        "UPDATE lessons SET title = ?, content = ?, order_num = ? WHERE id = ?",
        (data.get("title", ""), data.get("content", ""), data.get("order_num", 1), lesson_id)
    )
    return jsonify({"ok": True})


@app.route("/api/lessons/<int:lesson_id>", methods=["DELETE"])
def api_delete_lesson(lesson_id):
    db = DatabaseManager()
    db.execute("DELETE FROM lesson_progress WHERE lesson_id = ?", (lesson_id,))
    db.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
