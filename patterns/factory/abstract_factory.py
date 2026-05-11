# patterns/factory/abstract_factory.py — Abstract Factory Pattern
#
# Создаёт готовые учебные пакеты (курс + набор декораторов) по тарифу:
#   BasicPackageFactory    — курс без доп. опций
#   StandardPackageFactory — курс + Certificate
#   PremiumPackageFactory  — курс + Certificate + MentorSupport + LifetimeAccess

from abc import ABC, abstractmethod
from patterns.decorator.course_decorator import CourseComponent, CourseBuilder


class LearningPackageFactory(ABC):
    """Абстрактная фабрика учебных пакетов."""

    @abstractmethod
    def create_package(self, course: CourseComponent) -> CourseComponent:
        """Принимает базовый курс, возвращает декорированный пакет."""
        pass

    @property
    @abstractmethod
    def tier_name(self) -> str:
        pass


class BasicPackageFactory(LearningPackageFactory):
    """Базовый тариф — курс без дополнений."""

    @property
    def tier_name(self) -> str:
        return "basic"

    def create_package(self, course: CourseComponent) -> CourseComponent:
        return CourseBuilder(course).build()


class StandardPackageFactory(LearningPackageFactory):
    """Стандартный тариф — курс + сертификат."""

    @property
    def tier_name(self) -> str:
        return "standard"

    def create_package(self, course: CourseComponent) -> CourseComponent:
        return CourseBuilder(course).add("certificate").build()


class PremiumPackageFactory(LearningPackageFactory):
    """Премиум тариф — курс + сертификат + поддержка ментора + пожизненный доступ."""

    @property
    def tier_name(self) -> str:
        return "premium"

    def create_package(self, course: CourseComponent) -> CourseComponent:
        return (
            CourseBuilder(course)
            .add("certificate")
            .add("mentor_support")
            .add("lifetime_access")
            .build()
        )


# Реестр фабрик по названию тарифа
PACKAGE_FACTORIES: dict[str, LearningPackageFactory] = {
    "basic":    BasicPackageFactory(),
    "standard": StandardPackageFactory(),
    "premium":  PremiumPackageFactory(),
}


def get_package_factory(tier: str) -> LearningPackageFactory:
    tier = tier.lower()
    if tier not in PACKAGE_FACTORIES:
        raise ValueError(f"Unknown tier: '{tier}'. Use: {list(PACKAGE_FACTORIES)}")
    return PACKAGE_FACTORIES[tier]
