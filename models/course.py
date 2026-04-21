# models/course.py
from __future__ import annotations
from dataclasses import dataclass, field
from patterns.observer.course_observer import CourseSubject
from patterns.observer.event_bus import EventBus, LessonAddedEvent


@dataclass
class Course(CourseSubject):
    id: int
    title: str
    description: str
    price: float
    difficulty_level: str
    enrolled_students: list = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    def get_price(self) -> float:
        return self.price

    def get_description(self) -> str:
        return f"{self.title} [{self.difficulty_level}] — ${self.price:.2f}"

    def get_max_students(self) -> int:
        return 100

    def get_support_level(self) -> str:
        return "community"

    def add_lesson(self, lesson_title: str) -> None:
        self.notify_observers(self.title, f"New lesson added: '{lesson_title}'")
        EventBus().publish(LessonAddedEvent(
            course_title=self.title, lesson_title=lesson_title
        ))

    def __str__(self):
        return self.get_description()


@dataclass
class BasicCourse(Course):
    """
    Базовый курс: без ограничений по числу студентов,
    поддержка только через форум.
    """
    difficulty_level: str = field(default="basic", init=False)

    def get_max_students(self) -> int:
        return 500

    def get_support_level(self) -> str:
        return "forum"


@dataclass
class AdvancedCourse(Course):
    """
    Продвинутый курс: ограничен 100 студентами,
    поддержка через чат с ментором.
    """
    difficulty_level: str = field(default="advanced", init=False)

    def get_max_students(self) -> int:
        return 100

    def get_support_level(self) -> str:
        return "chat"


@dataclass
class ProfessionalCourse(Course):
    """
    Профессиональный курс: ограничен 30 студентами,
    персональная поддержка ментора.
    """
    difficulty_level: str = field(default="professional", init=False)

    def get_max_students(self) -> int:
        return 30

    def get_support_level(self) -> str:
        return "personal mentor"
