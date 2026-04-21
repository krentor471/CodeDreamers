# patterns/proxy/course_service_proxy.py — Proxy Pattern
#
# CourseServiceProxy стоит между Flask API и DatabaseManager.
# Отвечает за:
#   - контроль доступа по роли
#   - кэширование списка курсов и уроков в памяти

from __future__ import annotations
import logging
from database import DatabaseManager

logger = logging.getLogger(__name__)

# Права доступа к ресурсам по роли
_PERMISSIONS: dict[str, set[str]] = {
    "student": {"courses", "lessons", "enrollments", "program"},
    "mentor":  {"courses", "lessons", "enrollments", "program", "users"},
    "admin":   {"courses", "lessons", "enrollments", "program", "users", "analytics"},
}


class CourseServiceProxy:
    """
    Proxy для доступа к данным.
    Принимает role при создании, проверяет права перед каждым запросом.
    Кэширует courses и lessons в памяти на время сессии.
    """

    def __init__(self, role: str = "student"):
        self._role = role
        self._db = DatabaseManager()
        self._cache: dict[str, list] = {}

    def _check(self, resource: str) -> None:
        allowed = _PERMISSIONS.get(self._role, set())
        if resource not in allowed:
            raise PermissionError(
                f"Role '{self._role}' has no access to '{resource}'"
            )

    def get_courses(self) -> list:
        self._check("courses")
        if "courses" not in self._cache:
            rows = self._db.fetchall(
                "SELECT id, title, description, price, difficulty_level FROM courses ORDER BY id"
            )
            self._cache["courses"] = [dict(r) for r in rows]
            logger.info("Proxy: courses loaded from DB and cached")
        else:
            logger.info("Proxy: courses served from cache")
        return self._cache["courses"]

    def get_course(self, course_id: int) -> dict | None:
        self._check("courses")
        courses = self.get_courses()
        return next((c for c in courses if c["id"] == course_id), None)

    def get_lessons(self, course_id: int) -> list:
        self._check("lessons")
        key = f"lessons_{course_id}"
        if key not in self._cache:
            rows = self._db.fetchall(
                "SELECT id, course_id, title, content, order_num "
                "FROM lessons WHERE course_id=? ORDER BY order_num",
                (course_id,)
            )
            self._cache[key] = [dict(r) for r in rows]
            logger.info(f"Proxy: lessons for course {course_id} loaded and cached")
        else:
            logger.info(f"Proxy: lessons for course {course_id} served from cache")
        return self._cache[key]

    def get_program(self, course_id: int) -> dict:
        """Строит дерево LearningProgram для курса и возвращает как dict."""
        self._check("program")
        from patterns.composite.learning_composite import (
            LearningProgram, CourseBlock, LessonItem
        )
        course = self.get_course(course_id)
        if not course:
            return {}
        lessons = self.get_lessons(course_id)

        program = LearningProgram(course["title"])
        # Группируем уроки по блокам: каждые 3 урока — один блок
        block_size = 3
        for i in range(0, len(lessons), block_size):
            chunk = lessons[i:i + block_size]
            block_num = i // block_size + 1
            block = CourseBlock(f"Block {block_num}")
            for l in chunk:
                block.add(LessonItem(
                    id=l["id"],
                    title=l["title"],
                    content=l["content"],
                    order_num=l["order_num"],
                ))
            program.add_block(block)

        return program.to_dict()

    def get_enrollments(self, user_id: int) -> list:
        self._check("enrollments")
        rows = self._db.fetchall(
            """SELECT e.course_id, e.status, e.completed, c.title
               FROM enrollments e
               JOIN courses c ON e.course_id = c.id
               WHERE e.user_id = ?""",
            (user_id,)
        )
        return [dict(r) for r in rows]

    def get_users(self) -> list:
        self._check("users")
        rows = self._db.fetchall(
            "SELECT id, name, email, role FROM users ORDER BY id"
        )
        return [dict(r) for r in rows]

    def invalidate_cache(self) -> None:
        self._cache.clear()
        logger.info("Proxy: cache invalidated")
