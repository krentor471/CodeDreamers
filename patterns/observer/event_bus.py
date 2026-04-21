# patterns/observer/event_bus.py — Системная шина событий (Singleton + Observer)
#
# EventBus — единственный экземпляр в системе (Singleton).
# Любой модуль может:
#   - опубликовать событие:  EventBus().publish(event)
#   - подписаться на тип:    EventBus().subscribe(EventType, handler)
#
# Поддерживаемые события:
#   EnrollEvent        — студент записался на курс
#   UnenrollEvent      — студент отписался
#   CompleteEvent      — студент завершил курс
#   StateChangedEvent  — смена состояния Enrollment
#   LessonAddedEvent   — добавлен новый урок в курс
#   AnalyticsEvent     — аналитический запрос выполнен
#   NotificationEvent  — отправлено уведомление

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
import logging

logger = logging.getLogger(__name__)


# ── Базовый класс события ─────────────────────────────────────────────────

@dataclass
class SystemEvent:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


# ── Конкретные события системы ────────────────────────────────────────────

@dataclass
class EnrollEvent(SystemEvent):
    user_name: str = ""
    user_id: int = 0
    course_title: str = ""
    course_id: int = 0

@dataclass
class UnenrollEvent(SystemEvent):
    user_name: str = ""
    user_id: int = 0
    course_title: str = ""
    course_id: int = 0

@dataclass
class CompleteEvent(SystemEvent):
    user_name: str = ""
    user_id: int = 0
    course_title: str = ""
    course_id: int = 0

@dataclass
class StateChangedEvent(SystemEvent):
    label: str = ""
    from_state: str = ""
    to_state: str = ""

@dataclass
class LessonAddedEvent(SystemEvent):
    course_title: str = ""
    lesson_title: str = ""

@dataclass
class AnalyticsEvent(SystemEvent):
    report_type: str = ""
    result_summary: str = ""

@dataclass
class NotificationEvent(SystemEvent):
    channel: str = ""
    recipient: str = ""
    message: str = ""


# ── Шина событий (Singleton + Observer) ──────────────────────────────────

class EventBus:
    """
    Глобальная шина событий.
    Singleton — один экземпляр на всё приложение.
    Хранит подписчиков по типу события и рассылает им события при публикации.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # тип события -> список обработчиков
            cls._instance._subscribers: dict[str, list[Callable]] = {}
            cls._instance._event_log: list[SystemEvent] = []
        return cls._instance

    def subscribe(self, event_class: type, handler: Callable[[SystemEvent], None]) -> None:
        key = event_class.__name__
        self._subscribers.setdefault(key, [])
        if handler not in self._subscribers[key]:
            self._subscribers[key].append(handler)
            logger.debug(f"[EventBus] subscribed {handler.__self__.__class__.__name__} to {key}")

    def unsubscribe(self, event_class: type, handler: Callable) -> None:
        key = event_class.__name__
        if key in self._subscribers:
            self._subscribers[key] = [h for h in self._subscribers[key] if h != handler]

    def publish(self, event: SystemEvent) -> None:
        self._event_log.append(event)
        key = event.event_type
        handlers = self._subscribers.get(key, [])
        logger.debug(f"[EventBus] publish {key} -> {len(handlers)} subscribers")
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"[EventBus] handler error in {handler}: {e}")

    def get_log(self, event_class: type = None) -> list[SystemEvent]:
        """Возвращает лог событий, опционально фильтруя по типу."""
        if event_class is None:
            return list(self._event_log)
        key = event_class.__name__
        return [e for e in self._event_log if e.event_type == key]

    def clear_log(self) -> None:
        self._event_log.clear()
