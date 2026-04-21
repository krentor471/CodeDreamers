# patterns/template/content_generator.py — Template Method Pattern
#
# ContentGenerator определяет скелет алгоритма генерации учебного материала:
#   generate() -> intro() + body() + exercises() + summary()
#
# Подклассы переопределяют шаги, не меняя общий алгоритм.

from __future__ import annotations
from abc import ABC, abstractmethod


class ContentGenerator(ABC):
    """Абстрактный генератор учебного контента (Template Method)."""

    def generate(self, topic: str) -> str:
        """Шаблонный метод — фиксирует порядок шагов."""
        parts = [
            self.intro(topic),
            self.body(topic),
            self.exercises(topic),
            self.summary(topic),
        ]
        return "\n".join(parts)

    @abstractmethod
    def intro(self, topic: str) -> str: ...

    @abstractmethod
    def body(self, topic: str) -> str: ...

    @abstractmethod
    def exercises(self, topic: str) -> str: ...

    def summary(self, topic: str) -> str:
        """Хук — подклассы могут переопределить, но не обязаны."""
        return f"[Summary] Keep practising: {topic}."


class TextContentGenerator(ContentGenerator):
    """Генерирует текстовый конспект урока."""

    def intro(self, topic: str) -> str:
        return f"[Text] Introduction to {topic}."

    def body(self, topic: str) -> str:
        return f"[Text] Core concepts of {topic}: definitions, examples, best practices."

    def exercises(self, topic: str) -> str:
        return f"[Text] Exercises: write 3 examples using {topic}."


class VideoContentGenerator(ContentGenerator):
    """Генерирует сценарий видеоурока."""

    def intro(self, topic: str) -> str:
        return f"[Video] Scene 1 — Hook: why {topic} matters."

    def body(self, topic: str) -> str:
        return f"[Video] Scene 2 — Screencast: live coding with {topic}."

    def exercises(self, topic: str) -> str:
        return f"[Video] Scene 3 — Challenge: pause and solve the {topic} task."

    def summary(self, topic: str) -> str:
        return f"[Video] Scene 4 — Recap & subscribe for more {topic} content!"


class QuizContentGenerator(ContentGenerator):
    """Генерирует тест-опросник по теме."""

    def intro(self, topic: str) -> str:
        return f"[Quiz] Test your knowledge of {topic}."

    def body(self, topic: str) -> str:
        return (
            f"[Quiz] Q1: What is {topic}?\n"
            f"[Quiz] Q2: When should you use {topic}?\n"
            f"[Quiz] Q3: Name a real-world example of {topic}."
        )

    def exercises(self, topic: str) -> str:
        return f"[Quiz] Practical: implement a mini-project using {topic}."
