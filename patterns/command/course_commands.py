# patterns/command/course_commands.py — Command Pattern
# Команды теперь меняют состояние через EnrollmentContext (State Machine)
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from models.user import User
from models.course import Course
from database import DatabaseManager
from patterns.state.enrollment_state import EnrollmentContext, ActiveState
from patterns.observer.event_bus import EventBus, EnrollEvent, UnenrollEvent, CompleteEvent

logger = logging.getLogger(__name__)


class Command(ABC):
    @abstractmethod
    def execute(self) -> str:
        pass

    @abstractmethod
    def undo(self) -> str:
        pass


class DeleteCourseCommand(Command):
    """Удаляет курс из БД. Undo — восстанавливает (если реализовано)."""

    def __init__(self, course_id: int):
        self._course_id = course_id
        self._backup_data = None  # для undo (опционально)

    def execute(self) -> str:
        from database import DatabaseManager
        db = DatabaseManager()

        # Сохраняем данные перед удалением (для undo)
        course_row = db.fetchone("SELECT id, title FROM courses WHERE id = ?", (self._course_id,))
        if not course_row:
            raise ValueError(f"Курс с ID={self._course_id} не найден")

        self._backup_data = dict(course_row)

        # Удаляем зависимости
        db.execute("DELETE FROM course_tags WHERE course_id = ?", (self._course_id,))
        db.execute("DELETE FROM lessons WHERE course_id = ?", (self._course_id,))
        db.execute("DELETE FROM enrollments WHERE course_id = ?", (self._course_id,))
        db.execute("DELETE FROM modules WHERE course_id = ?", (self._course_id,))
        # Удаляем сам курс
        db.execute("DELETE FROM courses WHERE id = ?", (self._course_id,))

        msg = f"Курс '{self._backup_data['title']}' (ID={self._course_id}) удалён"
        return msg

    def undo(self) -> str:
        if not self._backup_data:
            return "UNDO: невозможно восстановить — нет данных"

        from database import DatabaseManager
        db = DatabaseManager()
        db.execute(
            "INSERT INTO courses (id, title, description, price, category) VALUES (?, ?, ?, ?, ?)",
            (
                self._backup_data["id"],
                self._backup_data["title"],
                self._backup_data.get("description", ""),
                self._backup_data.get("price", 0),
                self._backup_data.get("category", "basic"),
            )
        )
        return f"UNDO: курс '{self._backup_data['title']}' восстановлен"



class EnrollCommand(Command):
    def __init__(self, user: User, course: Course):
        self._user = user
        self._course = course

    def execute(self) -> str:
        db = DatabaseManager()
        try:
            db.execute(
                "INSERT INTO enrollments (user_id, course_id, status) VALUES (?, ?, 'active')",
                (self._user.id, self._course.id)
            )
            if self._user.id not in self._course.enrolled_students:
                self._course.enrolled_students.append(self._user.id)
            msg = f"{self._user.name} enrolled in '{self._course.title}' [ACTIVE]"
            logger.info(msg)
            EventBus().publish(EnrollEvent(
                user_name=self._user.name, user_id=self._user.id,
                course_title=self._course.title, course_id=self._course.id
            ))
            return msg
        except Exception:
            # Уже записан — пробуем переоткрыть через State Machine
            ctx = EnrollmentContext.load(
                self._user.id, self._course.id,
                self._user.name, self._course.title
            )
            return ctx.enroll()

    def undo(self) -> str:
        ctx = EnrollmentContext.load(
            self._user.id, self._course.id,
            self._user.name, self._course.title
        )
        result = ctx.cancel()
        self._course.enrolled_students = [
            s for s in self._course.enrolled_students if s != self._user.id
        ]
        EventBus().publish(UnenrollEvent(
            user_name=self._user.name, user_id=self._user.id,
            course_title=self._course.title, course_id=self._course.id
        ))
        return f"UNDO: {result}"


class UnenrollCommand(Command):
    def __init__(self, user: User, course: Course):
        self._user = user
        self._course = course

    def execute(self) -> str:
        ctx = EnrollmentContext.load(
            self._user.id, self._course.id,
            self._user.name, self._course.title
        )
        result = ctx.cancel()
        self._course.enrolled_students = [
            s for s in self._course.enrolled_students if s != self._user.id
        ]
        return result

    def undo(self) -> str:
        ctx = EnrollmentContext.load(
            self._user.id, self._course.id,
            self._user.name, self._course.title
        )
        return ctx.reopen()


class CompleteCourseCommand(Command):
    def __init__(self, user: User, course: Course):
        self._user = user
        self._course = course

    def execute(self) -> str:
        ctx = EnrollmentContext.load(
            self._user.id, self._course.id,
            self._user.name, self._course.title
        )
        result = ctx.complete()
        EventBus().publish(CompleteEvent(
            user_name=self._user.name, user_id=self._user.id,
            course_title=self._course.title, course_id=self._course.id
        ))
        return result

    def undo(self) -> str:
        ctx = EnrollmentContext.load(
            self._user.id, self._course.id,
            self._user.name, self._course.title
        )
        return f"UNDO: {ctx.reopen()}"


class CommandHistory:
    def __init__(self):
        self._history: list[Command] = []

    def execute(self, command: Command) -> str:
        result = command.execute()
        self._history.append(command)
        return result

    def undo_last(self) -> str:
        if not self._history:
            return "Nothing to undo"
        return self._history.pop().undo()
