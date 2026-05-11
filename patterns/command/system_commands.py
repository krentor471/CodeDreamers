# patterns/command/system_commands.py — Команды для всех операций системы
#
# Все задачи системы реализованы через интерфейс Command:
#
#   Пользователи:
#     CreateUserCommand      — создать пользователя через UserFactory
#     ChangeStrategyCommand  — сменить стратегию уведомлений
#
#   Курсы:
#     CreateCourseCommand    — создать курс через CourseFactory
#     AddLessonCommand       — добавить урок в курс
#     ApplyDecoratorCommand  — применить декоратор к курсу через CourseBuilder
#
#   Аналитика:
#     RevenueReportCommand   — получить отчёт по выручке
#     TopStudentsCommand     — получить топ студентов
#
#   Рекомендации:
#     RecommendCommand       — получить рекомендации для студента
#
#   Подписки:
#     SubscribeCommand       — подписать студента на курс (Observer)
#     UnsubscribeCommand     — отписать студента от курса

from __future__ import annotations
import logging
from abc import ABC, abstractmethod

from models.user import User
from models.course import Course
from patterns.observer.event_bus import EventBus, LessonAddedEvent, NotificationEvent

logger = logging.getLogger(__name__)


class Command(ABC):
    @abstractmethod
    def execute(self) -> str:
        pass

    @abstractmethod
    def undo(self) -> str:
        pass


# ── Пользователи ──────────────────────────────────────────────────────────

class CreateUserCommand(Command):
    """Создаёт пользователя через UserFactory. Undo — удаляет из БД."""

    def __init__(self, name: str, email: str, role: str):
        self._name = name
        self._email = email
        self._role = role
        self._created_user: User | None = None

    def execute(self) -> str:
        from patterns.factory.user_factory import UserFactory
        self._created_user = UserFactory.create(self._name, self._email, self._role)
        msg = (f"Created {self._created_user.__class__.__name__}: "
               f"'{self._name}' [{self._role}] "
               f"strategy={self._created_user._strategy.channel_name}")
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._created_user:
            from database import DatabaseManager
            DatabaseManager().execute(
                "DELETE FROM users WHERE id = ?", (self._created_user.id,)
            )
            msg = f"UNDO: deleted user '{self._name}' (id={self._created_user.id})"
            logger.info(msg)
            self._created_user = None
            return msg
        return "UNDO: nothing to undo"

    @property
    def result(self) -> User | None:
        return self._created_user


class ChangeStrategyCommand(Command):
    """Меняет стратегию уведомлений у пользователя. Undo — возвращает прежнюю."""

    def __init__(self, user: User, new_strategy):
        self._user = user
        self._new_strategy = new_strategy
        self._old_strategy = user._strategy

    def execute(self) -> str:
        self._user.set_notification_strategy(self._new_strategy)
        msg = (f"Strategy changed for '{self._user.name}': "
               f"{self._old_strategy.channel_name} -> {self._new_strategy.channel_name}")
        logger.info(msg)
        return msg

    def undo(self) -> str:
        self._user.set_notification_strategy(self._old_strategy)
        msg = (f"UNDO: strategy restored for '{self._user.name}': "
               f"{self._new_strategy.channel_name} -> {self._old_strategy.channel_name}")
        logger.info(msg)
        return msg


# ── Курсы ─────────────────────────────────────────────────────────────────

class CreateCourseCommand(Command):
    """Создаёт курс через CourseFactory. Undo — удаляет из БД."""

    def __init__(self, title: str, description: str,
                 base_price: float, category: str, tags: list[str] = None):
        self._title = title
        self._description = description
        self._base_price = base_price
        self._category = category
        self._tags = tags or []
        self._created_course: Course | None = None

    def execute(self) -> str:
        from patterns.factory.course_factory import CourseFactory
        self._created_course = CourseFactory.create(
            self._title, self._description,
            self._base_price, self._category, self._tags
        )
        msg = (f"Created {self._created_course.__class__.__name__}: "
               f"'{self._title}' ${self._created_course.get_price():.2f} "
               f"max={self._created_course.get_max_students()} "
               f"support={self._created_course.get_support_level()}")
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._created_course:
            from database import DatabaseManager
            db = DatabaseManager()
            db.execute("DELETE FROM course_tags WHERE course_id = ?",
                       (self._created_course.id,))
            db.execute("DELETE FROM courses WHERE id = ?",
                       (self._created_course.id,))
            msg = f"UNDO: deleted course '{self._title}' (id={self._created_course.id})"
            logger.info(msg)
            self._created_course = None
            return msg
        return "UNDO: nothing to undo"

    @property
    def result(self) -> Course | None:
        return self._created_course


class AddLessonCommand(Command):
    """Добавляет урок в курс. Undo — удаляет урок из БД."""

    def __init__(self, course: Course, title: str, content: str, order_num: int, module_id: int = None):
        self._course = course
        self._title = title
        self._content = content
        self._order_num = order_num
        self._module_id = module_id
        self._lesson_id: int | None = None

    def execute(self) -> str:
        from database import DatabaseManager
        cursor = DatabaseManager().execute(
            "INSERT INTO lessons (course_id, module_id, title, content, order_num) VALUES (?, ?, ?, ?, ?)",
            (self._course.id, self._module_id, self._title, self._content, self._order_num)
        )
        self._lesson_id = cursor.lastrowid
        self._course.add_lesson(self._title)
        msg = f"Lesson added to '{self._course.title}': #{self._order_num} '{self._title}'"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._lesson_id:
            from database import DatabaseManager
            DatabaseManager().execute(
                "DELETE FROM lessons WHERE id = ?", (self._lesson_id,)
            )
            msg = f"UNDO: removed lesson '{self._title}' from '{self._course.title}'"
            logger.info(msg)
            self._lesson_id = None
            return msg
        return "UNDO: nothing to undo"


class ApplyDecoratorCommand(Command):
    """Применяет декораторы к курсу через CourseBuilder. Undo — удаляет пакет из БД."""

    def __init__(self, course: Course, options: list[str]):
        self._course = course
        self._options = options
        self._package_id: int | None = None
        self._result = None

    def execute(self) -> str:
        from patterns.decorator.course_decorator import CourseBuilder
        from database import DatabaseManager
        self._result = CourseBuilder(self._course)
        for opt in self._options:
            self._result = self._result.add(opt)
        self._result = self._result.build()
        row = DatabaseManager().fetchone(
            "SELECT id FROM course_packages WHERE course_id=? ORDER BY id DESC LIMIT 1",
            (self._course.id,)
        )
        if row:
            self._package_id = row["id"]
        msg = (f"Package created for '{self._course.title}': "
               f"{', '.join(self._options)} -> ${self._result.get_price():.2f}")
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._package_id:
            from database import DatabaseManager
            DatabaseManager().execute(
                "DELETE FROM course_packages WHERE id = ?", (self._package_id,)
            )
            msg = f"UNDO: removed package (id={self._package_id}) for '{self._course.title}'"
            logger.info(msg)
            self._package_id = None
            return msg
        return "UNDO: nothing to undo"

    @property
    def result(self):
        return self._result


# ── Аналитика ─────────────────────────────────────────────────────────────

class RevenueReportCommand(Command):
    """Запрашивает отчёт по выручке через AnalyticsAdapter."""

    def __init__(self):
        self._report: dict | None = None

    def execute(self) -> str:
        from patterns.adapter.analytics_adapter import AnalyticsAdapter
        self._report = AnalyticsAdapter().revenue_report()
        msg = f"RevenueReport generated: total=${self._report['total']:.2f}"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        self._report = None
        return "UNDO: RevenueReport cleared (read-only, no DB changes)"

    @property
    def result(self) -> dict | None:
        return self._report


class TopStudentsCommand(Command):
    """Запрашивает топ студентов через AnalyticsAdapter."""

    def __init__(self, top_n: int = 3):
        self._top_n = top_n
        self._result: list | None = None

    def execute(self) -> str:
        from patterns.adapter.analytics_adapter import AnalyticsAdapter
        self._result = AnalyticsAdapter().top_students(self._top_n)
        names = [s["uname"] for s in self._result]
        msg = f"TopStudents(top={self._top_n}): {names}"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        self._result = None
        return "UNDO: TopStudents cleared (read-only)"

    @property
    def result(self) -> list | None:
        return self._result


# ── Рекомендации ──────────────────────────────────────────────────────────

class RecommendCommand(Command):
    """Получает рекомендации курсов для студента."""

    def __init__(self, user: User, top_n: int = 3):
        self._user = user
        self._top_n = top_n
        self._result: list | None = None

    def execute(self) -> str:
        from services.recommendation_service import recommend_courses
        self._result = recommend_courses(self._user.id, self._top_n)
        titles = [r["title"] for r in self._result]
        msg = f"Recommendations for '{self._user.name}': {titles}"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        self._result = None
        return "UNDO: Recommendations cleared (read-only)"

    @property
    def result(self) -> list | None:
        return self._result


# ── Template Method — генерация контента ────────────────────────────────

class GenerateContentCommand(Command):
    """Генерирует учебный контент через Template Method."""

    _GENERATORS = {
        "text":  "TextContentGenerator",
        "video": "VideoContentGenerator",
        "quiz":  "QuizContentGenerator",
    }

    def __init__(self, topic: str, format: str = "text"):
        self._topic = topic
        self._format = format.lower()
        self._result: str | None = None

    def execute(self) -> str:
        from patterns.template.content_generator import (
            TextContentGenerator, VideoContentGenerator, QuizContentGenerator
        )
        generators = {
            "text":  TextContentGenerator,
            "video": VideoContentGenerator,
            "quiz":  QuizContentGenerator,
        }
        cls = generators.get(self._format)
        if cls is None:
            raise ValueError(f"Unknown format '{self._format}'. Use: {list(generators)}")
        self._result = cls().generate(self._topic)
        msg = f"Content generated [{self._format}] for topic: '{self._topic}'"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        self._result = None
        return f"UNDO: GenerateContent cleared (read-only)"

    @property
    def result(self) -> str | None:
        return self._result


class ChangeStateCommand(Command):
    """Изменяет состояние курса. Undo — возвращает предыдущее состояние."""

    def __init__(self, course_id: int, action: str):
        self._course_id = course_id
        self._action = action
        self._old_state = None
        self._new_state = None

    def execute(self) -> str:
        from patterns.state.course_state import CourseContext
        from database import DatabaseManager
        
        # Получаем текущее состояние
        db = DatabaseManager()
        row = db.fetchone("SELECT state FROM courses WHERE id = ?", (self._course_id,))
        if not row:
            raise ValueError(f"Course with ID={self._course_id} not found")
        
        self._old_state = row["state"] or "new"
        
        # Выполняем переход
        ctx = CourseContext.load(self._course_id)
        result = getattr(ctx, self._action)()
        
        # Получаем новое состояние
        row = db.fetchone("SELECT state FROM courses WHERE id = ?", (self._course_id,))
        self._new_state = row["state"] if row else "new"
        
        msg = f"State changed: {self._old_state} → {self._new_state}"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._old_state is None:
            return "UNDO: no state to restore"
        
        from database import DatabaseManager
        DatabaseManager().execute(
            "UPDATE courses SET state = ? WHERE id = ?",
            (self._old_state, self._course_id)
        )
        
        msg = f"UNDO: state restored {self._new_state} → {self._old_state}"
        logger.info(msg)
        return msg


class SendNotificationCommand(Command):
    """Отправляет уведомление. Undo — удаляет из лога (если возможно)."""

    def __init__(self, message: str, recipient: str = "all"):
        self._message = message
        self._recipient = recipient
        self._notification_id = None

    def execute(self) -> str:
        from patterns.observer.event_bus import EventBus, NotificationEvent
        from database import DatabaseManager
        
        # Сохраняем в БД для возможности отмены
        db = DatabaseManager()
        cursor = db.execute(
            "INSERT INTO notifications (channel, recipient, message, timestamp) VALUES (?, ?, ?, datetime('now'))",
            ("web", self._recipient, self._message)
        )
        self._notification_id = cursor.lastrowid
        
        # Отправляем через EventBus
        EventBus().publish(NotificationEvent(
            channel="web", recipient=self._recipient, message=self._message
        ))
        
        msg = f"Notification sent to {self._recipient}: {self._message[:50]}..."
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._notification_id:
            from database import DatabaseManager
            DatabaseManager().execute(
                "DELETE FROM notifications WHERE id = ?", (self._notification_id,)
            )
            msg = f"UNDO: notification deleted (id={self._notification_id})"
            logger.info(msg)
            return msg
        return "UNDO: nothing to undo"


class CreateModuleCommand(Command):
    """Создает модуль в курсе. Undo — удаляет модуль из БД."""

    def __init__(self, course_id: int, title: str, order_num: int, teacher_id: int = None):
        self._course_id = course_id
        self._title = title
        self._order_num = order_num
        self._teacher_id = teacher_id
        self._module_id: int | None = None

    def execute(self) -> str:
        from database import DatabaseManager
        cursor = DatabaseManager().execute(
            "INSERT INTO modules (course_id, title, order_num, teacher_id) VALUES (?, ?, ?, ?)",
            (self._course_id, self._title, self._order_num, self._teacher_id)
        )
        self._module_id = cursor.lastrowid
        msg = f"Module created in course {self._course_id}: '{self._title}'"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._module_id:
            from database import DatabaseManager
            db = DatabaseManager()
            db.execute("DELETE FROM module_disciplines WHERE module_id = ?", (self._module_id,))
            db.execute("DELETE FROM modules WHERE id = ?", (self._module_id,))
            msg = f"UNDO: removed module '{self._title}' (id={self._module_id})"
            logger.info(msg)
            self._module_id = None
            return msg
        return "UNDO: nothing to undo"

    @property
    def result(self) -> dict | None:
        if self._module_id:
            return {"id": self._module_id, "title": self._title, "order_num": self._order_num}
        return None


class AddDisciplineToModuleCommand(Command):
    """Добавляет предмет в модуль. Undo — удаляет связь."""

    def __init__(self, module_id: int, discipline_id: int, order_num: int = 1):
        self._module_id = module_id
        self._discipline_id = discipline_id
        self._order_num = order_num
        self._link_id: int | None = None

    def execute(self) -> str:
        from database import DatabaseManager
        cursor = DatabaseManager().execute(
            "INSERT OR IGNORE INTO module_disciplines (module_id, discipline_id, order_num) VALUES (?, ?, ?)",
            (self._module_id, self._discipline_id, self._order_num)
        )
        self._link_id = cursor.lastrowid if cursor.lastrowid else self._get_link_id()
        msg = f"Discipline {self._discipline_id} added to module {self._module_id}"
        logger.info(msg)
        return msg

    def _get_link_id(self) -> int | None:
        from database import DatabaseManager
        row = DatabaseManager().fetchone(
            "SELECT id FROM module_disciplines WHERE module_id=? AND discipline_id=?",
            (self._module_id, self._discipline_id)
        )
        return row["id"] if row else None

    def undo(self) -> str:
        if self._link_id:
            from database import DatabaseManager
            DatabaseManager().execute(
                "DELETE FROM module_disciplines WHERE id = ?", (self._link_id,)
            )
            msg = f"UNDO: removed discipline link (id={self._link_id})"
            logger.info(msg)
            return msg
        return "UNDO: nothing to undo"


class CreateDisciplineCommand(Command):
    """Создает новый предмет (дисциплину). Undo — удаляет из БД."""

    def __init__(self, title: str, description: str = "", content: str = ""):
        self._title = title
        self._description = description
        self._content = content
        self._discipline_id: int | None = None

    def execute(self) -> str:
        from database import DatabaseManager
        cursor = DatabaseManager().execute(
            "INSERT INTO disciplines (title, description, content) VALUES (?, ?, ?)",
            (self._title, self._description, self._content)
        )
        self._discipline_id = cursor.lastrowid
        msg = f"Discipline created: '{self._title}' (id={self._discipline_id})"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._discipline_id:
            from database import DatabaseManager
            db = DatabaseManager()
            db.execute("DELETE FROM module_disciplines WHERE discipline_id = ?", (self._discipline_id,))
            db.execute("DELETE FROM disciplines WHERE id = ?", (self._discipline_id,))
            msg = f"UNDO: removed discipline '{self._title}' (id={self._discipline_id})"
            logger.info(msg)
            self._discipline_id = None
            return msg
        return "UNDO: nothing to undo"

    @property
    def result(self) -> dict | None:
        if self._discipline_id:
            return {"id": self._discipline_id, "title": self._title}
        return None


# ── Подписки Observer ─────────────────────────────────────────────────────

class SubscribeCommand(Command):
    """Подписывает студента на обновления курса (Observer)."""

    def __init__(self, user: User, course: Course):
        self._user = user
        self._course = course
        self._observer = None

    def execute(self) -> str:
        from services.student_observer import StudentObserver
        self._observer = StudentObserver(self._user)
        self._course.subscribe(self._observer)
        msg = f"'{self._user.name}' subscribed to '{self._course.title}'"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        if self._observer and self._observer in self._course._observers:
            self._course.unsubscribe(self._observer)
            msg = f"UNDO: '{self._user.name}' unsubscribed from '{self._course.title}'"
            logger.info(msg)
            return msg
        return "UNDO: not subscribed"
