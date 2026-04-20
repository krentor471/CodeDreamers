# patterns/command/course_commands.py — Command Pattern
# Команды теперь меняют состояние через EnrollmentContext (State Machine)
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from models.user import User
from models.course import Course
from database import DatabaseManager
from patterns.state.enrollment_state import EnrollmentContext, ActiveState

logger = logging.getLogger(__name__)


class Command(ABC):
    @abstractmethod
    def execute(self) -> str:
        pass

    @abstractmethod
    def undo(self) -> str:
        pass


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
        return ctx.complete()

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
