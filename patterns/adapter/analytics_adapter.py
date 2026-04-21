# patterns/adapter/analytics_adapter.py — Adapter Pattern
#
# ПРОБЛЕМА:
#   ExternalAnalytics работает со словарями формата:
#     {"uid", "uname", "urole", "cenrolled", "cprice", ...}
#
#   Система CodeDreamers работает с объектами:
#     User, Course, DatabaseManager
#
#   Эти интерфейсы несовместимы — нельзя передать User напрямую в ExternalAnalytics.
#
# РЕШЕНИЕ — Адаптер:
#   AnalyticsAdapter реализует интерфейс IAnalytics (ожидаемый системой),
#   внутри преобразует объекты системы в формат ExternalAnalytics и вызывает её.
#
# Схема:
#
#   Система                  Адаптер                  Внешний модуль
#   ─────────────────────    ─────────────────────    ──────────────────────
#   IAnalytics               AnalyticsAdapter         ExternalAnalytics
#   + enrollment_rate()  --> + enrollment_rate()  --> + get_course_enrollment_rate()
#   + completion_rate()  --> + completion_rate()  --> + get_student_completion_rate()
#   + revenue_report()   --> + revenue_report()   --> + get_revenue_report()
#   + top_students()     --> + top_students()     --> + get_top_students()

from __future__ import annotations
from abc import ABC, abstractmethod
import logging

from models.user import User
from models.course import Course
from database import DatabaseManager
from services.analytics_service import ExternalAnalytics

logger = logging.getLogger(__name__)


# ── Целевой интерфейс (Target) ────────────────────────────────────────────
# Именно этот интерфейс ожидает система CodeDreamers.
# Работает с внутренними объектами: User, Course.

class IAnalytics(ABC):
    @abstractmethod
    def enrollment_rate(self, course: Course) -> float:
        """Процент пользователей системы, записанных на курс."""
        pass

    @abstractmethod
    def completion_rate(self, user: User) -> float:
        """Процент завершённых курсов у студента."""
        pass

    @abstractmethod
    def revenue_report(self) -> dict:
        """Отчёт по выручке по всем курсам."""
        pass

    @abstractmethod
    def top_students(self, top_n: int = 3) -> list[dict]:
        """Топ студентов по количеству завершённых курсов."""
        pass


# ── Адаптер (Adapter) ─────────────────────────────────────────────────────
# Реализует IAnalytics (интерфейс системы),
# внутри преобразует данные и делегирует ExternalAnalytics.

class AnalyticsAdapter(IAnalytics):
    """
    Адаптер подключает ExternalAnalytics к системе CodeDreamers.

    Преобразования:
      Course  -->  {"cid", "cname", "clevel", "cprice", "cenrolled"}
      User    -->  {"uid", "uname", "urole"}
      enrollment row --> {"estatus"}
    """

    def __init__(self):
        self._analytics = ExternalAnalytics()   # адаптируемый объект (Adaptee)
        self._db = DatabaseManager()

    # ── Преобразователи объектов системы в формат ExternalAnalytics ──────

    def _course_to_record(self, course: Course) -> dict:
        enrolled_count = self._db.fetchone(
            "SELECT COUNT(*) as n FROM enrollments WHERE course_id = ?",
            (course.id,)
        )["n"]
        return {
            "cid":      course.id,
            "cname":    course.title,
            "clevel":   course.difficulty_level,
            "cprice":   course.get_price(),
            "cenrolled": enrolled_count,
        }

    def _user_to_record(self, user: User) -> dict:
        return {
            "uid":   user.id,
            "uname": user.name,
            "urole": user.role,
        }

    def _enrollment_rows_for_user(self, user: User) -> list[dict]:
        rows = self._db.fetchall(
            "SELECT status FROM enrollments WHERE user_id = ?", (user.id,)
        )
        return [{"estatus": row["status"]} for row in rows]

    # ── Реализация IAnalytics через ExternalAnalytics ─────────────────────

    def enrollment_rate(self, course: Course) -> float:
        total_users = self._db.fetchone(
            "SELECT COUNT(*) as n FROM users"
        )["n"]
        course_record = self._course_to_record(course)
        return self._analytics.get_course_enrollment_rate(
            course_record, total_users
        )

    def completion_rate(self, user: User) -> float:
        user_record = self._user_to_record(user)
        enrollments = self._enrollment_rows_for_user(user)
        return self._analytics.get_student_completion_rate(
            user_record, enrollments
        )

    def revenue_report(self) -> dict:
        rows = self._db.fetchall("SELECT id, title, price, difficulty_level FROM courses")
        course_records = []
        for row in rows:
            enrolled_count = self._db.fetchone(
                "SELECT COUNT(*) as n FROM enrollments WHERE course_id = ?",
                (row["id"],)
            )["n"]
            course_records.append({
                "cname":    row["title"],
                "cprice":   row["price"],
                "cenrolled": enrolled_count,
            })
        return self._analytics.get_revenue_report(course_records)

    def top_students(self, top_n: int = 3) -> list[dict]:
        users = self._db.fetchall(
            "SELECT id, name FROM users WHERE role = 'student'"
        )
        student_records = []
        for u in users:
            completed = self._db.fetchone(
                "SELECT COUNT(*) as n FROM enrollments "
                "WHERE user_id = ? AND status = 'completed'",
                (u["id"],)
            )["n"]
            student_records.append({
                "uname":      u["name"],
                "ucompleted": completed,
            })
        return self._analytics.get_top_students(student_records, top_n)
