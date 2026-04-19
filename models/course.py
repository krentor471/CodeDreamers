# models/course.py
from __future__ import annotations
from dataclasses import dataclass, field
from patterns.observer.course_observer import CourseSubject

@dataclass
class Course(CourseSubject):
    id: int
    title: str
    description: str
    price: float
    difficulty_level: str  # basic | advanced | professional
    enrolled_students: list = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    def get_price(self) -> float:
        return self.price

    def get_description(self) -> str:
        return f"{self.title} [{self.difficulty_level}] — ${self.price:.2f}"

    def add_lesson(self, lesson_title: str) -> None:
        self.notify_observers(self.title, f"New lesson added: '{lesson_title}'")

    def __str__(self):
        return self.get_description()
