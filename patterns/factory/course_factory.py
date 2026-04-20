# patterns/factory/course_factory.py — Factory Method Pattern
from __future__ import annotations
import logging
from models.course import Course, BasicCourse, AdvancedCourse, ProfessionalCourse
from database import DatabaseManager

logger = logging.getLogger(__name__)

# Маппинг категории -> (подкласс, множитель цены)
_COURSE_CLASSES: dict[str, tuple[type, float]] = {
    "basic":        (BasicCourse,        1.0),
    "advanced":     (AdvancedCourse,     1.5),
    "professional": (ProfessionalCourse, 2.0),
}


class CourseFactory:
    @staticmethod
    def create(title: str, description: str, base_price: float,
               category: str, tags: list[str] = None) -> Course:
        category = category.lower()
        if category not in _COURSE_CLASSES:
            raise ValueError(f"Unknown category: '{category}'. Use: {list(_COURSE_CLASSES)}")

        cls, multiplier = _COURSE_CLASSES[category]
        price = round(base_price * multiplier, 2)

        db = DatabaseManager()
        cursor = db.execute(
            "INSERT INTO courses (title, description, price, difficulty_level) VALUES (?, ?, ?, ?)",
            (title, description, price, category)
        )
        course_id = cursor.lastrowid

        for tag in (tags or []):
            db.execute(
                "INSERT OR IGNORE INTO course_tags (course_id, tag) VALUES (?, ?)",
                (course_id, tag.lower())
            )

        # Создаём специализированный подкласс
        course = cls(id=course_id, title=title, description=description, price=price)
        logger.info(
            f"Created {cls.__name__}: '{title}' ${price} "
            f"| max_students={course.get_max_students()} "
            f"| support={course.get_support_level()}"
        )
        return course
