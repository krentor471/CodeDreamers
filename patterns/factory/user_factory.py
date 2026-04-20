# patterns/factory/user_factory.py — Factory Method Pattern
from __future__ import annotations
import logging
from models.user import User
from database import DatabaseManager
from patterns.strategy.notification_strategy import DEFAULT_STRATEGY

logger = logging.getLogger(__name__)

class UserFactory:
    _role_map = {"student", "mentor", "admin"}

    @staticmethod
    def create(name: str, email: str, role: str) -> User:
        role = role.lower()
        if role not in UserFactory._role_map:
            raise ValueError(f"Unknown role: {role}. Use: {UserFactory._role_map}")

        db = DatabaseManager()
        try:
            cursor = db.execute(
                "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
                (name, email, role)
            )
            # Назначаем стратегию уведомлений по умолчанию согласно роли:
            #   student -> Email, mentor -> Telegram, admin -> SMS
            strategy = DEFAULT_STRATEGY[role]
            user = User(id=cursor.lastrowid, name=name, email=email,
                        role=role, _strategy=strategy)
            logger.info(f"Created user: {user} | strategy: {strategy.channel_name}")
            return user
        except Exception as e:
            row = db.fetchone("SELECT * FROM users WHERE email = ?", (email,))
            if row:
                strategy = DEFAULT_STRATEGY[role]
                return User(id=row["id"], name=row["name"], email=row["email"],
                            role=row["role"], _strategy=strategy)
            raise e
