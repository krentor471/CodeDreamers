# services/recommendation_service.py — математическая модель: косинусное сходство
#
# Идея:
#   Каждый курс описывается вектором тегов: {"python": 1, "algorithms": 1, "web": 0, ...}
#   Профиль студента — сумма векторов всех пройденных им курсов.
#   Сходство студента с новым курсом = косинус угла между двумя векторами:
#
#       similarity(A, B) = (A · B) / (|A| * |B|)
#
#   Чем ближе значение к 1.0 — тем больше курс подходит студенту.
#   Курсы, на которые студент уже записан, исключаются из рекомендаций.

import math
import logging
from database import DatabaseManager

logger = logging.getLogger(__name__)


def _dot_product(a: dict, b: dict) -> float:
    """Скалярное произведение двух векторов, представленных словарями."""
    return sum(a.get(tag, 0) * b.get(tag, 0) for tag in b)


def _magnitude(vec: dict) -> float:
    """Длина (модуль) вектора."""
    return math.sqrt(sum(v * v for v in vec.values()))


def cosine_similarity(a: dict, b: dict) -> float:
    """
    Косинусное сходство между векторами a и b.
    Возвращает значение от 0.0 (нет сходства) до 1.0 (полное совпадение).
    """
    mag_a = _magnitude(a)
    mag_b = _magnitude(b)
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return _dot_product(a, b) / (mag_a * mag_b)


def _get_course_vector(course_id: int, db: DatabaseManager) -> dict:
    """Возвращает вектор тегов курса: {"python": 1, "web": 1, ...}"""
    tags = db.fetchall(
        "SELECT tag FROM course_tags WHERE course_id = ?", (course_id,)
    )
    return {row["tag"]: 1 for row in tags}


def _get_student_profile(user_id: int, db: DatabaseManager) -> dict:
    """
    Строит профиль студента как сумму векторов всех курсов,
    на которые он записан (включая завершённые).
    Завершённые курсы имеют вес 2 — они сильнее влияют на профиль.
    """
    enrollments = db.fetchall(
        "SELECT course_id, completed FROM enrollments WHERE user_id = ?", (user_id,)
    )
    profile: dict = {}
    for row in enrollments:
        weight = 2 if row["completed"] else 1
        vec = _get_course_vector(row["course_id"], db)
        for tag, val in vec.items():
            profile[tag] = profile.get(tag, 0) + val * weight
    return profile


def recommend_courses(user_id: int, top_n: int = 3) -> list[dict]:
    """
    Возвращает top_n курсов, наиболее подходящих студенту,
    на которые он ещё не записан.

    Каждый элемент результата:
        {"course_id": int, "title": str, "similarity": float, "tags": list[str]}
    """
    db = DatabaseManager()

    # Курсы, на которые студент уже записан
    enrolled = {
        row["course_id"]
        for row in db.fetchall(
            "SELECT course_id FROM enrollments WHERE user_id = ?", (user_id,)
        )
    }

    # Профиль студента
    profile = _get_student_profile(user_id, db)
    logger.info(f"Student {user_id} profile vector: {profile}")

    if not profile:
        # Студент ещё нигде не учился — возвращаем просто первые top_n курсов
        rows = db.fetchall("SELECT id, title FROM courses LIMIT ?", (top_n,))
        return [{"course_id": r["id"], "title": r["title"],
                 "similarity": 0.0, "tags": []} for r in rows]

    # Считаем сходство для каждого курса, на который студент НЕ записан
    all_courses = db.fetchall("SELECT id, title FROM courses")
    scores = []
    for course in all_courses:
        if course["id"] in enrolled:
            continue
        vec = _get_course_vector(course["id"], db)
        if not vec:
            continue
        sim = cosine_similarity(profile, vec)
        scores.append({
            "course_id": course["id"],
            "title": course["title"],
            "similarity": round(sim, 4),
            "tags": list(vec.keys()),
        })

    # Сортируем по убыванию сходства
    scores.sort(key=lambda x: x["similarity"], reverse=True)
    logger.info(f"Recommendations for user {user_id}: {scores[:top_n]}")
    return scores[:top_n]
