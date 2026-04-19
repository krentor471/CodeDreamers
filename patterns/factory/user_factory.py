# patterns/factory/user_factory.py — Factory Method Pattern
from __future__ import annotations
import logging
from models.user import User
from database import DatabaseManager

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
            user = User(id=cursor.lastrowid, name=name, email=email, role=role)
            logger.info(f"Created user: {user}")
            return user
        except Exception as e:
            # Return in-memory user if DB insert fails (e.g. duplicate email in demo)
            row = db.fetchone("SELECT * FROM users WHERE email = ?", (email,))
            if row:
                return User(id=row["id"], name=row["name"], email=row["email"], role=row["role"])
            raise e
