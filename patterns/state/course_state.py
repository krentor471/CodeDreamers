# patterns/state/course_state.py — State Machine для Course
#
# Диаграмма состояний курса:
#
#   NEW --assign_mentor()--> ASSIGNED_TO_MENTOR --assign_user()--> ASSIGNED_TO_USER
#                                                                         |
#                                                                   start_progress()
#                                                                         |
#                                                                   IN_PROGRESS --complete()--> COMPLETED

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from patterns.observer.event_bus import EventBus, StateChangedEvent

logger = logging.getLogger(__name__)


class CourseState(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property
    @abstractmethod
    def display_name(self) -> str: pass
    
    @property
    @abstractmethod
    def color(self) -> str: pass

    def assign_mentor(self, ctx: "CourseContext") -> str:
        return f"[{ctx.label}] Cannot assign mentor in state '{self.name}'"

    def assign_user(self, ctx: "CourseContext") -> str:
        return f"[{ctx.label}] Cannot assign user in state '{self.name}'"

    def start_progress(self, ctx: "CourseContext") -> str:
        return f"[{ctx.label}] Cannot start in state '{self.name}'"

    def complete(self, ctx: "CourseContext") -> str:
        return f"[{ctx.label}] Cannot complete in state '{self.name}'"


class NewCourseState(CourseState):
    @property
    def name(self) -> str: return "new"
    
    @property
    def display_name(self) -> str: return "Новый"
    
    @property
    def color(self) -> str: return "#6c757d"

    def assign_mentor(self, ctx: "CourseContext") -> str:
        ctx._transition(AssignedToMentorState())
        return f"[{ctx.label}] new -> assigned_to_mentor"


class AssignedToMentorState(CourseState):
    @property
    def name(self) -> str: return "assigned_to_mentor"
    
    @property
    def display_name(self) -> str: return "Прикреплен к преподу"
    
    @property
    def color(self) -> str: return "#17a2b8"

    def assign_user(self, ctx: "CourseContext") -> str:
        ctx._transition(AssignedToUserState())
        return f"[{ctx.label}] assigned_to_mentor -> assigned_to_user"


class AssignedToUserState(CourseState):
    @property
    def name(self) -> str: return "assigned_to_user"
    
    @property
    def display_name(self) -> str: return "Прикреплен к юзеру"
    
    @property
    def color(self) -> str: return "#ffc107"

    def start_progress(self, ctx: "CourseContext") -> str:
        ctx._transition(InProgressState())
        return f"[{ctx.label}] assigned_to_user -> in_progress"


class InProgressState(CourseState):
    @property
    def name(self) -> str: return "in_progress"
    
    @property
    def display_name(self) -> str: return "Выполняется"
    
    @property
    def color(self) -> str: return "#007bff"

    def complete(self, ctx: "CourseContext") -> str:
        ctx._transition(CompletedCourseState())
        return f"[{ctx.label}] in_progress -> completed"


class CompletedCourseState(CourseState):
    @property
    def name(self) -> str: return "completed"
    
    @property
    def display_name(self) -> str: return "Пройден"
    
    @property
    def color(self) -> str: return "#28a745"


_STATE_MAP: dict[str, CourseState] = {
    "new":                NewCourseState(),
    "assigned_to_mentor": AssignedToMentorState(),
    "assigned_to_user":   AssignedToUserState(),
    "in_progress":        InProgressState(),
    "completed":          CompletedCourseState(),
}


class CourseContext:
    def __init__(self, course_id: int, title: str, state: CourseState = None):
        self.course_id = course_id
        self.label = title
        self.state: CourseState = state or NewCourseState()

    def _transition(self, new_state: CourseState) -> None:
        old = self.state.name
        self.state = new_state
        self._save()
        EventBus().publish(StateChangedEvent(
            label=self.label, from_state=old, to_state=new_state.name
        ))
        logger.info(f"CourseState [{self.label}]: {old} -> {new_state.name}")

    def _save(self) -> None:
        from database import DatabaseManager
        DatabaseManager().execute(
            "UPDATE courses SET state = ? WHERE id = ?",
            (self.state.name, self.course_id)
        )

    def assign_mentor(self) -> str:  return self.state.assign_mentor(self)
    def assign_user(self)   -> str:  return self.state.assign_user(self)
    def start_progress(self) -> str: return self.state.start_progress(self)
    def complete(self)       -> str: return self.state.complete(self)

    @property
    def status(self) -> str: return self.state.name

    @classmethod
    def load(cls, course_id: int) -> "CourseContext":
        from database import DatabaseManager
        row = DatabaseManager().fetchone(
            "SELECT title, state FROM courses WHERE id = ?", (course_id,)
        )
        if not row:
            raise ValueError(f"Course {course_id} not found")
        state = _STATE_MAP.get(row["state"] or "new", NewCourseState())
        return cls(course_id, row["title"], state)
