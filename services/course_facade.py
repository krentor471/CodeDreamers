# services/course_facade.py — Facade Pattern
from __future__ import annotations
import logging
from database import DatabaseManager

logger = logging.getLogger(__name__)


class CourseFacade:
    def __init__(self):
        self._db = DatabaseManager()

    # ── Создание курса ────────────────────────────────────────────────────

    def create_course(self, title: str, description: str,
                      price: float, category: str,
                      tags: list[str] = None) -> dict:
        from patterns.command.system_commands import CreateCourseCommand
        from patterns.command.course_commands import CommandHistory
        cmd = CreateCourseCommand(title, description, price, category, tags or [])
        CommandHistory().execute(cmd)
        course = cmd.result
        self._db.execute("UPDATE courses SET state = 'new' WHERE id = ?", (course.id,))
        logger.info(f"[Facade] create_course: '{title}' id={course.id}")
        return {
            "id": course.id, "title": course.title,
            "price": course.get_price(), "difficulty_level": course.difficulty_level,
            "state": "new", "tags": tags or [],
        }

    # ── Добавление урока ──────────────────────────────────────────────────

    def add_lesson(self, course_id: int, title: str, content: str, order_num: int) -> dict:
        from patterns.command.system_commands import AddLessonCommand
        from patterns.command.course_commands import CommandHistory
        from models.course import Course
        row = self._db.fetchone("SELECT * FROM courses WHERE id = ?", (course_id,))
        if not row:
            raise ValueError(f"Course {course_id} not found")
        course = Course(id=row["id"], title=row["title"], description=row["description"],
                        price=row["price"], difficulty_level=row["difficulty_level"])
        cmd = AddLessonCommand(course, title, content, order_num)
        CommandHistory().execute(cmd)
        logger.info(f"[Facade] add_lesson: '{title}' -> course {course_id}")
        return {"course_id": course_id, "title": title, "content": content, "order_num": order_num}

    # ── Теги ──────────────────────────────────────────────────────────────

    def set_tags(self, course_id: int, tags: list[str]) -> list[str]:
        self._db.execute("DELETE FROM course_tags WHERE course_id = ?", (course_id,))
        for tag in tags:
            self._db.execute(
                "INSERT OR IGNORE INTO course_tags (course_id, tag) VALUES (?, ?)",
                (course_id, tag.lower().strip())
            )
        logger.info(f"[Facade] set_tags course={course_id}: {tags}")
        return tags

    def suggest_tags(self, description: str) -> list[str]:
        from patterns.adapter.ai_adapter import AIAdapter
        return AIAdapter().suggest_tags(description)

    # ── Состояние курса ───────────────────────────────────────────────────

    def transition_state(self, course_id: int, action: str) -> dict:
        from patterns.state.course_state import CourseContext
        ctx = CourseContext.load(course_id)
        actions = {
            "assign_mentor":  ctx.assign_mentor,
            "assign_user":    ctx.assign_user,
            "start_progress": ctx.start_progress,
            "complete":       ctx.complete,
        }
        if action not in actions:
            raise ValueError(f"Unknown action '{action}'. Use: {list(actions)}")
        msg = actions[action]()
        return {"course_id": course_id, "state": ctx.status, "message": msg}

    def get_state(self, course_id: int) -> dict:
        from patterns.state.course_state import CourseContext
        ctx = CourseContext.load(course_id)
        return {"course_id": course_id, "state": ctx.status}

    # ── Пакет (Abstract Factory + Decorator) ─────────────────────────────

    def get_package(self, course_id: int, tier: str) -> dict:
        from patterns.factory.abstract_factory import get_package_factory
        from models.course import Course
        row = self._db.fetchone("SELECT * FROM courses WHERE id = ?", (course_id,))
        if not row:
            raise ValueError(f"Course {course_id} not found")
        course = Course(id=row["id"], title=row["title"], description=row["description"],
                        price=row["price"], difficulty_level=row["difficulty_level"])
        factory = get_package_factory(tier)
        package = factory.create_package(course)
        return {
            "course_id": course_id, "tier": factory.tier_name,
            "description": package.get_description(),
            "final_price": round(package.get_price(), 2),
        }

    # ── AI ────────────────────────────────────────────────────────────────

    def ask_ai(self, course_id: int, question: str) -> str:
        from patterns.adapter.ai_adapter import AIAdapter
        return AIAdapter().ask(course_id, question)

    def generate_quiz(self, topic: str, count: int = 3) -> list[dict]:
        from patterns.adapter.ai_adapter import AIAdapter
        return AIAdapter().generate_quiz(topic, count)

    # ── Аналитика ─────────────────────────────────────────────────────────

    def revenue_report(self) -> dict:
        from patterns.command.system_commands import RevenueReportCommand
        from patterns.command.course_commands import CommandHistory
        cmd = RevenueReportCommand()
        CommandHistory().execute(cmd)
        return cmd.result

    def top_students(self, top_n: int = 3) -> list[dict]:
        from patterns.command.system_commands import TopStudentsCommand
        from patterns.command.course_commands import CommandHistory
        cmd = TopStudentsCommand(top_n)
        CommandHistory().execute(cmd)
        return cmd.result

    # ── Вектор рекомендаций (мат. модель) ────────────────────────────────

    def get_recommendation_vector(self, user_id: int) -> dict:
        from services.recommendation_service import (
            _get_student_profile, _get_course_vector, cosine_similarity
        )
        db = self._db
        profile = _get_student_profile(user_id, db)
        enrolled = {
            r["course_id"] for r in db.fetchall(
                "SELECT course_id FROM enrollments WHERE user_id = ?", (user_id,)
            )
        }
        courses = db.fetchall("SELECT id, title FROM courses")
        vectors = []
        for c in courses:
            vec = _get_course_vector(c["id"], db)
            if not vec:
                continue
            sim = cosine_similarity(profile, vec) if profile else 0.0
            vectors.append({
                "course_id": c["id"],
                "title": c["title"],
                "similarity": round(sim, 4),
                "enrolled": c["id"] in enrolled,
                "tags": list(vec.keys()),
            })
        vectors.sort(key=lambda x: x["similarity"], reverse=True)
        return {
            "user_id": user_id,
            "profile_tags": list(profile.keys()) if profile else [],
            "vectors": vectors,
        }
