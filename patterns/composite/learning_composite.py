# patterns/composite/learning_composite.py — Composite Pattern
#
# Иерархия учебного контента:
#   LearningProgram (корень)
#   └── CourseBlock  (блок: HTML, CSS, JS)
#       └── LessonItem (лист — конкретный урок)
#
# Все узлы реализуют единый интерфейс CourseComponent.

from __future__ import annotations
from abc import ABC, abstractmethod


class LearningComponent(ABC):
    """Общий интерфейс для всех узлов дерева."""

    @abstractmethod
    def get_title(self) -> str: ...

    @abstractmethod
    def get_children(self) -> list["LearningComponent"]: ...

    @abstractmethod
    def get_type(self) -> str: ...

    def to_dict(self) -> dict:
        result = {"title": self.get_title(), "type": self.get_type()}
        children = self.get_children()
        if children:
            result["children"] = [c.to_dict() for c in children]
        return result


class LessonItem(LearningComponent):
    """Лист дерева — конкретный урок."""

    def __init__(self, id: int, title: str, content: str, order_num: int):
        self.id = id
        self.title = title
        self.content = content
        self.order_num = order_num

    def get_title(self) -> str:
        return self.title

    def get_children(self) -> list:
        return []

    def get_type(self) -> str:
        return "lesson"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "order_num": self.order_num,
            "type": "lesson",
        }


class CourseBlock(LearningComponent):
    """Составной узел — блок курса (например, 'HTML', 'CSS', 'JS')."""

    def __init__(self, title: str):
        self.title = title
        self._children: list[LearningComponent] = []

    def add(self, component: LearningComponent) -> "CourseBlock":
        self._children.append(component)
        return self

    def get_title(self) -> str:
        return self.title

    def get_children(self) -> list[LearningComponent]:
        return self._children

    def get_type(self) -> str:
        return "block"


class LearningProgram(LearningComponent):
    """Корень дерева — программа обучения, содержит блоки."""

    def __init__(self, title: str):
        self.title = title
        self._blocks: list[CourseBlock] = []

    def add_block(self, block: CourseBlock) -> "LearningProgram":
        self._blocks.append(block)
        return self

    def get_title(self) -> str:
        return self.title

    def get_children(self) -> list[LearningComponent]:
        return self._blocks

    def get_type(self) -> str:
        return "program"
