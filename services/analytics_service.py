# services/analytics_service.py — внешняя аналитическая система
#
# Это "сторонний модуль" с собственным интерфейсом и форматом данных.
# Он НЕ знает о классах User, Course, DatabaseManager.
# Работает только со словарями своего формата:
#
#   user_record  = {"uid": int, "uname": str, "urole": str}
#   course_record = {"cid": int, "cname": str, "clevel": str, "cprice": float}
#
# Именно из-за несовместимости интерфейсов нужен Адаптер.

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ExternalAnalytics:
    """
    Внешняя аналитическая система.
    Принимает данные только в своём формате (словари с префиксами u/c).
    Не знает ничего о внутренних классах системы CodeDreamers.
    """

    def get_course_enrollment_rate(self, course_record: dict,
                                   total_users: int) -> float:
        """
        Процент пользователей системы, записанных на курс.
        course_record: {"cid", "cname", "cenrolled"}
        """
        if total_users == 0:
            return 0.0
        rate = round(course_record["cenrolled"] / total_users * 100, 2)
        logger.info(f"[Analytics] enrollment_rate '{course_record['cname']}': {rate}%")
        return rate

    def get_student_completion_rate(self, user_record: dict,
                                    enrollments: list[dict]) -> float:
        """
        Процент завершённых курсов у студента.
        enrollments: [{"estatus": str}, ...]
        """
        if not enrollments:
            return 0.0
        completed = sum(1 for e in enrollments if e["estatus"] == "completed")
        rate = round(completed / len(enrollments) * 100, 2)
        logger.info(
            f"[Analytics] completion_rate '{user_record['uname']}': {rate}%"
        )
        return rate

    def get_revenue_report(self, course_records: list[dict]) -> dict:
        """
        Отчёт по выручке.
        course_records: [{"cname", "cprice", "cenrolled"}, ...]
        Возвращает: {"total": float, "by_course": [{"name", "revenue"}, ...]}
        """
        report = {"generated_at": datetime.now().isoformat(), "by_course": []}
        total = 0.0
        for c in course_records:
            revenue = round(c["cprice"] * c["cenrolled"], 2)
            total += revenue
            report["by_course"].append({
                "name": c["cname"],
                "revenue": revenue,
                "enrolled": c["cenrolled"],
            })
        report["total"] = round(total, 2)
        logger.info(f"[Analytics] revenue_report total: ${report['total']}")
        return report

    def get_top_students(self, student_records: list[dict],
                         top_n: int = 3) -> list[dict]:
        """
        Топ студентов по количеству завершённых курсов.
        student_records: [{"uname", "ucompleted"}, ...]
        """
        sorted_students = sorted(
            student_records,
            key=lambda s: s["ucompleted"],
            reverse=True
        )
        top = sorted_students[:top_n]
        logger.info(f"[Analytics] top_students: {[s['uname'] for s in top]}")
        return top
