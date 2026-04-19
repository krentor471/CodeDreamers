# patterns/decorator/course_decorator.py — Decorator Pattern
from __future__ import annotations
from abc import ABC, abstractmethod

class CourseComponent(ABC):
    @abstractmethod
    def get_price(self) -> float:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

class CourseDecorator(CourseComponent):
    def __init__(self, course: CourseComponent):
        self._course = course

    def get_price(self) -> float:
        return self._course.get_price()

    def get_description(self) -> str:
        return self._course.get_description()

class WithCertificate(CourseDecorator):
    _extra = 49.99

    def get_price(self) -> float:
        return self._course.get_price() + self._extra

    def get_description(self) -> str:
        return self._course.get_description() + " + [Certificate]"

class WithMentorSupport(CourseDecorator):
    _extra = 99.99

    def get_price(self) -> float:
        return self._course.get_price() + self._extra

    def get_description(self) -> str:
        return self._course.get_description() + " + [Mentor Support]"

class WithLifetimeAccess(CourseDecorator):
    _extra = 29.99

    def get_price(self) -> float:
        return self._course.get_price() + self._extra

    def get_description(self) -> str:
        return self._course.get_description() + " + [Lifetime Access]"
