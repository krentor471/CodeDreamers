# patterns/command/course_commands.py — Command Pattern
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from models.user import User
from models.course import Course
from database import DatabaseManager

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
                "INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)",
                (self._user.id, self._course.id)
            )
            if self._user.id not in self._course.enrolled_students:
                self._course.enrolled_students.append(self._user.id)
            msg = f"{self._user.name} enrolled in '{self._course.title}'"
            logger.info(msg)
            return msg
        except Exception:
            return f"{self._user.name} is already enrolled in '{self._course.title}'"

    def undo(self) -> str:
        db = DatabaseManager()
        db.execute(
            "DELETE FROM enrollments WHERE user_id = ? AND course_id = ?",
            (self._user.id, self._course.id)
        )
        self._course.enrolled_students = [
            s for s in self._course.enrolled_students if s != self._user.id
        ]
        msg = f"UNDO: {self._user.name} unenrolled from '{self._course.title}'"
        logger.info(msg)
        return msg

class UnenrollCommand(Command):
    def __init__(self, user: User, course: Course):
        self._user = user
        self._course = course

    def execute(self) -> str:
        db = DatabaseManager()
        db.execute(
            "DELETE FROM enrollments WHERE user_id = ? AND course_id = ?",
            (self._user.id, self._course.id)
        )
        self._course.enrolled_students = [
            s for s in self._course.enrolled_students if s != self._user.id
        ]
        msg = f"{self._user.name} unenrolled from '{self._course.title}'"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        db = DatabaseManager()
        try:
            db.execute(
                "INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)",
                (self._user.id, self._course.id)
            )
            self._course.enrolled_students.append(self._user.id)
        except Exception:
            pass
        msg = f"UNDO: {self._user.name} re-enrolled in '{self._course.title}'"
        logger.info(msg)
        return msg

class CompleteCourseCommand(Command):
    def __init__(self, user: User, course: Course):
        self._user = user
        self._course = course

    def execute(self) -> str:
        db = DatabaseManager()
        db.execute(
            "UPDATE enrollments SET completed = 1 WHERE user_id = ? AND course_id = ?",
            (self._user.id, self._course.id)
        )
        msg = f"{self._user.name} completed '{self._course.title}' [DONE]"
        logger.info(msg)
        return msg

    def undo(self) -> str:
        db = DatabaseManager()
        db.execute(
            "UPDATE enrollments SET completed = 0 WHERE user_id = ? AND course_id = ?",
            (self._user.id, self._course.id)
        )
        msg = f"UNDO: '{self._course.title}' marked as incomplete for {self._user.name}"
        logger.info(msg)
        return msg

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
