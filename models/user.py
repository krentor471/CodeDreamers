# models/user.py
from __future__ import annotations
from dataclasses import dataclass, field
from patterns.strategy.notification_strategy import NotificationStrategy, EmailNotification

@dataclass
class User:
    id: int
    name: str
    email: str
    role: str  # student | mentor | admin
    _strategy: NotificationStrategy = field(default_factory=EmailNotification, repr=False)

    def set_notification_strategy(self, strategy: NotificationStrategy) -> None:
        self._strategy = strategy

    def notify(self, message: str) -> None:
        self._strategy.send(self.email, message)

    def __str__(self):
        return f"[{self.role.upper()}] {self.name} <{self.email}>"
