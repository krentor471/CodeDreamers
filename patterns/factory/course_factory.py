# patterns/factory/course_factory.py — Factory Method Pattern
from __future__ import annotations
import logging
from models.course import Course
from database import DatabaseManager

logger = logging.getLogger(__name__)

_DIFFICULTY = {
    "basic": {"level": "basic", "price_multiplier": 1.0},
    "advanced": {"level": "advanced", "price_multiplier": 1.5},
    "professional": {"level": "professional", "price_multiplier": 2.0},
}

class CourseFactory:
    @staticmethod
    def create(title: str, description: str, base_price: float, category: str) -> Course:
        category = category.lower()
        if category not in _DIFFICULTY:
            raise ValueError(f"Unknown category: {category}. Use: {list(_DIFFICULTY)}")

        cfg = _DIFFICULTY[category]
        price = round(base_price * cfg["price_multiplier"], 2)

        db = DatabaseManager()
        cursor = db.execute(
            "INSERT INTO courses (title, description, price, difficulty_level) VALUES (?, ?, ?, ?)",
            (title, description, price, cfg["level"])
        )
        course = Course(
            id=cursor.lastrowid,
            title=title,
            description=description,
            price=price,
            difficulty_level=cfg["level"]
        )
        logger.info(f"Created course: {course}")
        return course
