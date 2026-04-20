# models/user.py
from __future__ import annotations
from dataclasses import dataclass, field
from patterns.strategy.notification_strategy import NotificationStrategy, EmailNotification


@dataclass
class User:
    id: int
    name: str
    email: str
    role: str
    _strategy: NotificationStrategy = field(default_factory=EmailNotification, repr=False)

    def set_notification_strategy(self, strategy: NotificationStrategy) -> None:
        self._strategy = strategy

    def notify(self, message: str) -> None:
        self._strategy.send(self.email, message)

    def get_permissions(self) -> list[str]:
        return []

    def __str__(self):
        return f"[{self.role.upper()}] {self.name} <{self.email}>"


@dataclass
class Student(User):
    """Может записываться на курсы и получать рекомендации."""
    role: str = field(default="student", init=False)

    def get_permissions(self) -> list[str]:
        return ["enroll", "complete_course", "view_recommendations", "view_lessons"]

    def get_discount(self) -> float:
        """Студенты получают скидку 10% на все курсы."""
        return 0.10


@dataclass
class Mentor(User):
    """Может создавать курсы и уроки, видеть всех студентов."""
    role: str = field(default="mentor", init=False)

    def get_permissions(self) -> list[str]:
        return ["create_course", "add_lesson", "view_students", "enroll"]

    def get_hourly_rate(self) -> float:
        """Ставка ментора за час поддержки."""
        return 50.0


@dataclass
class Admin(User):
    """Полный доступ ко всем операциям."""
    role: str = field(default="admin", init=False)

    def get_permissions(self) -> list[str]:
        return ["enroll", "create_course", "add_lesson", "view_students",
                "delete_user", "delete_course", "manage_system"]

    def can_delete(self) -> bool:
        return True
