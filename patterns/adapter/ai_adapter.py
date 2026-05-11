# patterns/adapter/ai_adapter.py — AI Adapter
#
# IAIService  — целевой интерфейс системы
# ExternalAI  — внешний ИИ-модуль (имитация, легко заменить на OpenAI/Gemini)
# AIAdapter   — адаптирует ExternalAI к IAIService, обогащает контекстом из БД

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from database import DatabaseManager

logger = logging.getLogger(__name__)


# ── Целевой интерфейс ─────────────────────────────────────────────────────

class IAIService(ABC):
    @abstractmethod
    def ask(self, course_id: int, question: str) -> str:
        """Задать вопрос об курсе."""
        pass

    @abstractmethod
    def suggest_tags(self, description: str) -> list[str]:
        """Предложить теги по описанию курса."""
        pass

    @abstractmethod
    def generate_quiz(self, topic: str, count: int = 3) -> list[dict]:
        """Сгенерировать вопросы для теста."""
        pass


# ── Внешний ИИ-модуль (Adaptee) ───────────────────────────────────────────

class ExternalAI:
    """
    Внешний ИИ-сервис на базе g4f.
    Интерфейс несовместим с системой — принимает только plain-текст.
    """

    def query(self, prompt: str) -> str:
        import g4f
        logger.info(f"[ExternalAI] query: {prompt[:80]}...")
        try:
            return g4f.ChatCompletion.create(
                model=g4f.models.default,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            logger.error(f"[ExternalAI] query error: {e}")
            return f"Ошибка ИИ: {e}"

    def suggest(self, text: str) -> str:
        import g4f
        logger.info(f"[ExternalAI] suggest tags for: {text[:60]}")
        prompt = (
            f"Suggest 5 short lowercase tags (comma-separated, no spaces) "
            f"for a course with this description: {text}"
        )
        try:
            raw = g4f.ChatCompletion.create(
                model=g4f.models.default,
                messages=[{"role": "user", "content": prompt}],
            )
            return raw
        except Exception as e:
            logger.error(f"[ExternalAI] suggest error: {e}")
            return "programming,beginner"


# ── Адаптер ───────────────────────────────────────────────────────────────

class AIAdapter(IAIService):
    """
    Адаптирует ExternalAI к интерфейсу IAIService.
    Обогащает запросы контекстом курса из БД перед передачей в ExternalAI.
    """

    def __init__(self):
        self._ai = ExternalAI()
        self._db = DatabaseManager()

    def _get_course_context(self, course_id: int) -> str:
        row = self._db.fetchone(
            "SELECT title, description, difficulty_level FROM courses WHERE id = ?",
            (course_id,)
        )
        if not row:
            return ""
        tags = self._db.fetchall(
            "SELECT tag FROM course_tags WHERE course_id = ?", (course_id,)
        )
        tag_str = ", ".join(r["tag"] for r in tags)
        return (f"Курс: '{row['title']}' [{row['difficulty_level']}]. "
                f"Описание: {row['description']}. Теги: {tag_str}.")

    def ask(self, course_id: int, question: str) -> str:
        context = self._get_course_context(course_id)
        prompt = f"{context}\nВопрос студента: {question}"
        answer = self._ai.query(prompt)
        # Сохраняем в notifications как ai_chat
        self._db.execute(
            "INSERT INTO notifications (channel, recipient, message, sent_at) "
            "VALUES ('ai_chat', ?, ?, datetime('now'))",
            (str(course_id), f"Q: {question} | A: {answer}")
        )
        logger.info(f"[AIAdapter] ask course={course_id}: {question[:50]}")
        return answer

    def suggest_tags(self, description: str) -> list[str]:
        raw = self._ai.suggest(description)
        tags = [t.strip() for t in raw.split(",") if t.strip()]
        logger.info(f"[AIAdapter] suggest_tags: {tags}")
        return tags

    def generate_quiz(self, topic: str, count: int = 3) -> list[dict]:
        prompt = (
            f"Generate exactly {count} quiz questions about '{topic}'. "
            f"Format each line strictly as: Q: <question>|A: <answer>"
        )
        raw = self._ai.query(prompt)
        result = []
        for line in raw.strip().split("\n"):
            if "|" in line and ("Q:" in line or line.strip().startswith("Q")):
                parts = line.split("|")
                q = parts[0].split(":", 1)[-1].strip()
                a = parts[1].split(":", 1)[-1].strip() if len(parts) > 1 else ""
                if q:
                    result.append({"question": q, "answer": a})
        logger.info(f"[AIAdapter] generate_quiz topic='{topic}' count={len(result)}")
        return result[:count]
