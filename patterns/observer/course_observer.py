# patterns/observer/course_observer.py — Observer Pattern
from __future__ import annotations
from abc import ABC, abstractmethod

class CourseObserver(ABC):
    @abstractmethod
    def update(self, course_title: str, event: str) -> None:
        pass

class CourseSubject:
    def __init__(self):
        self._observers: list[CourseObserver] = []

    def subscribe(self, observer: CourseObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: CourseObserver) -> None:
        self._observers.remove(observer)

    def notify_observers(self, course_title: str, event: str) -> None:
        for obs in self._observers:
            obs.update(course_title, event)
