# patterns/iterator/learning_iterator.py — Iterator Pattern
#
# LearningIterator обходит дерево LearningProgram в глубину (DFS)
# и возвращает только листья — LessonItem.

from __future__ import annotations
from typing import Iterator
from patterns.composite.learning_composite import LearningComponent, LessonItem


class LearningIterator:
    """DFS-итератор по дереву LearningComponent, возвращает LessonItem."""

    def __init__(self, root: LearningComponent):
        self._stack: list[LearningComponent] = [root]

    def __iter__(self) -> Iterator[LessonItem]:
        return self

    def __next__(self) -> LessonItem:
        while self._stack:
            node = self._stack.pop()
            children = node.get_children()
            # Добавляем детей в обратном порядке, чтобы обходить слева направо
            self._stack.extend(reversed(children))
            if isinstance(node, LessonItem):
                return node
        raise StopIteration
