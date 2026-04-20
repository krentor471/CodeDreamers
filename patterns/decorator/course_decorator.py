# patterns/decorator/course_decorator.py — Decorator Pattern
from __future__ import annotations
from abc import ABC, abstractmethod
from database import DatabaseManager


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


# Маппинг названия опции -> декоратор
_DECORATORS: dict[str, type] = {
    "certificate":    WithCertificate,
    "mentor_support": WithMentorSupport,
    "lifetime_access": WithLifetimeAccess,
}


class CourseBuilder:
    """
    Строит декорированный курс через цепочку опций.
    Сохраняет итоговую цену и описание в БД (таблица course_packages).

    Пример:
        package = CourseBuilder(course).add("certificate").add("mentor_support").build()
    """

    def __init__(self, course: CourseComponent):
        self._course = course
        self._applied: list[str] = []

    def add(self, option: str) -> "CourseBuilder":
        option = option.lower()
        if option not in _DECORATORS:
            raise ValueError(f"Unknown option: '{option}'. Use: {list(_DECORATORS)}")
        self._course = _DECORATORS[option](self._course)
        self._applied.append(option)
        return self

    def build(self) -> CourseComponent:
        """Возвращает декорированный курс и сохраняет пакет в БД."""
        if self._applied:
            course_id = getattr(self._course, "id", None)
            # Достаём id из самого внутреннего объекта (оригинальный Course)
            obj = self._course
            while hasattr(obj, "_course"):
                obj = obj._course
            course_id = getattr(obj, "id", None)

            if course_id:
                db = DatabaseManager()
                db.execute(
                    "INSERT INTO course_packages (course_id, options, final_price, description) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        course_id,
                        ", ".join(self._applied),
                        round(self._course.get_price(), 2),
                        self._course.get_description(),
                    )
                )
        return self._course
