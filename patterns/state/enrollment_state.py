# patterns/state/enrollment_state.py — State Machine для Enrollment
#
# Диаграмма состояний Enrollment:
#
#   [*] --enroll()--> ACTIVE --complete()--> COMPLETED
#                      |                         |
#                  cancel()                  reopen()
#                      |                         |
#                      v                         v
#                  CANCELLED <--cancel()--    ACTIVE
#
# Таблица переходов:
#   Состояние  | Действие  | Новое состояние
#   -----------|-----------|----------------
#   (нет)      | enroll    | ACTIVE
#   ACTIVE     | complete  | COMPLETED
#   ACTIVE     | cancel    | CANCELLED
#   COMPLETED  | reopen    | ACTIVE
#   COMPLETED  | cancel    | CANCELLED
#   CANCELLED  | enroll    | ACTIVE
#   CANCELLED  | reopen    | ACTIVE

from __future__ import annotations
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class EnrollmentState(ABC):
    @abstractmethod
    def enroll(self, ctx: "EnrollmentContext") -> str:
        pass

    @abstractmethod
    def complete(self, ctx: "EnrollmentContext") -> str:
        pass

    @abstractmethod
    def cancel(self, ctx: "EnrollmentContext") -> str:
        pass

    @abstractmethod
    def reopen(self, ctx: "EnrollmentContext") -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class ActiveState(EnrollmentState):
    @property
    def name(self) -> str:
        return "ACTIVE"

    def enroll(self, ctx: "EnrollmentContext") -> str:
        return f"[{ctx.label}] Already ACTIVE"

    def complete(self, ctx: "EnrollmentContext") -> str:
        ctx.state = CompletedState()
        ctx._save()
        msg = f"[{ctx.label}] ACTIVE -> COMPLETED"
        logger.info(msg)
        return msg

    def cancel(self, ctx: "EnrollmentContext") -> str:
        ctx.state = CancelledState()
        ctx._save()
        msg = f"[{ctx.label}] ACTIVE -> CANCELLED"
        logger.info(msg)
        return msg

    def reopen(self, ctx: "EnrollmentContext") -> str:
        return f"[{ctx.label}] Already ACTIVE — cannot reopen"


class CompletedState(EnrollmentState):
    @property
    def name(self) -> str:
        return "COMPLETED"

    def enroll(self, ctx: "EnrollmentContext") -> str:
        return f"[{ctx.label}] Already COMPLETED — cannot re-enroll"

    def complete(self, ctx: "EnrollmentContext") -> str:
        return f"[{ctx.label}] Already COMPLETED"

    def cancel(self, ctx: "EnrollmentContext") -> str:
        ctx.state = CancelledState()
        ctx._save()
        msg = f"[{ctx.label}] COMPLETED -> CANCELLED"
        logger.info(msg)
        return msg

    def reopen(self, ctx: "EnrollmentContext") -> str:
        ctx.state = ActiveState()
        ctx._save()
        msg = f"[{ctx.label}] COMPLETED -> ACTIVE"
        logger.info(msg)
        return msg


class CancelledState(EnrollmentState):
    @property
    def name(self) -> str:
        return "CANCELLED"

    def enroll(self, ctx: "EnrollmentContext") -> str:
        ctx.state = ActiveState()
        ctx._save()
        msg = f"[{ctx.label}] CANCELLED -> ACTIVE (re-enrolled)"
        logger.info(msg)
        return msg

    def complete(self, ctx: "EnrollmentContext") -> str:
        return f"[{ctx.label}] Cannot complete — CANCELLED"

    def cancel(self, ctx: "EnrollmentContext") -> str:
        return f"[{ctx.label}] Already CANCELLED"

    def reopen(self, ctx: "EnrollmentContext") -> str:
        ctx.state = ActiveState()
        ctx._save()
        msg = f"[{ctx.label}] CANCELLED -> ACTIVE"
        logger.info(msg)
        return msg


# Маппинг строки из БД -> объект состояния
_STATE_MAP: dict[str, EnrollmentState] = {
    "active":    ActiveState(),
    "completed": CompletedState(),
    "cancelled": CancelledState(),
}


class EnrollmentContext:
    """
    Контекст машины состояний для одной записи (user + course).
    Синхронизирует состояние с полем status в таблице enrollments.
    """

    def __init__(self, user_id: int, course_id: int,
                 user_name: str, course_title: str,
                 initial_state: EnrollmentState = None):
        self.user_id = user_id
        self.course_id = course_id
        self.label = f"{user_name} / {course_title}"
        self.state: EnrollmentState = initial_state or ActiveState()

    def _save(self) -> None:
        """Сохраняет текущее состояние в БД."""
        from database import DatabaseManager
        completed = 1 if self.state.name == "COMPLETED" else 0
        DatabaseManager().execute(
            "UPDATE enrollments SET completed = ?, status = ? "
            "WHERE user_id = ? AND course_id = ?",
            (completed, self.state.name.lower(), self.user_id, self.course_id)
        )

    def enroll(self)   -> str: return self.state.enroll(self)
    def complete(self) -> str: return self.state.complete(self)
    def cancel(self)   -> str: return self.state.cancel(self)
    def reopen(self)   -> str: return self.state.reopen(self)

    @property
    def status(self) -> str:
        return self.state.name

    @classmethod
    def load(cls, user_id: int, course_id: int,
             user_name: str, course_title: str) -> "EnrollmentContext":
        """Загружает контекст из БД по текущему статусу записи."""
        from database import DatabaseManager
        row = DatabaseManager().fetchone(
            "SELECT status FROM enrollments WHERE user_id=? AND course_id=?",
            (user_id, course_id)
        )
        status = row["status"] if row and row["status"] else "active"
        state = _STATE_MAP.get(status, ActiveState())
        return cls(user_id, course_id, user_name, course_title, state)
