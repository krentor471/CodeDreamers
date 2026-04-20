# patterns/factory/user_factory.py — Factory Method Pattern
from __future__ import annotations
import logging
from models.user import User, Student, Mentor, Admin
from database import DatabaseManager
from patterns.strategy.notification_strategy import DEFAULT_STRATEGY

logger = logging.getLogger(__name__)

# Маппинг роли -> подкласс User
_USER_CLASSES: dict[str, type] = {
    "student": Student,
    "mentor":  Mentor,
    "admin":   Admin,
}


class UserFactory:
    @staticmethod
    def create(name: str, email: str, role: str) -> User:
        role = role.lower()
        if role not in _USER_CLASSES:
            raise ValueError(f"Unknown role: '{role}'. Use: {list(_USER_CLASSES)}")

        db = DatabaseManager()
        try:
            cursor = db.execute(
                "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
                (name, email, role)
            )
            user = UserFactory._build(cursor.lastrowid, name, email, role)
            logger.info(
                f"Created {user.__class__.__name__}: {user} "
                f"| strategy: {user._strategy.channel_name} "
                f"| permissions: {user.get_permissions()}"
            )
            return user
        except Exception as e:
            row = db.fetchone("SELECT * FROM users WHERE email = ?", (email,))
            if row:
                return UserFactory._build(row["id"], row["name"], row["email"], row["role"])
            raise e

    @staticmethod
    def _build(uid: int, name: str, email: str, role: str) -> User:
        """Создаёт экземпляр нужного подкласса с правильной стратегией."""
        cls = _USER_CLASSES[role]
        strategy = DEFAULT_STRATEGY[role]
        return cls(id=uid, name=name, email=email, _strategy=strategy)
