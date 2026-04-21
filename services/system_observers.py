# services/system_observers.py — подписчики системной шины событий
#
# Каждый модуль подписывается на нужные ему типы событий через EventBus.
# При публикации события шина вызывает update() у всех подписчиков.
#
# Модули:
#   LogObserver          — пишет все события в лог (следит за всем)
#   AuditObserver        — сохраняет критичные события в БД (audit_log)
#   AnalyticsObserver    — обновляет счётчики аналитики при событиях
#   NotificationObserver — отправляет уведомления при ключевых событиях

import logging
from database import DatabaseManager
from patterns.observer.event_bus import (
    EventBus,
    EnrollEvent, UnenrollEvent, CompleteEvent,
    StateChangedEvent, LessonAddedEvent,
    AnalyticsEvent, NotificationEvent,
)

logger = logging.getLogger(__name__)


class LogObserver:
    """
    Следит за ВСЕМИ событиями системы.
    Выводит каждое событие в консоль и лог.
    """

    def __init__(self):
        bus = EventBus()
        for event_cls in [EnrollEvent, UnenrollEvent, CompleteEvent,
                          StateChangedEvent, LessonAddedEvent,
                          AnalyticsEvent, NotificationEvent]:
            bus.subscribe(event_cls, self.update)

    def update(self, event) -> None:
        msg = f"[LOG] {event.event_type:<22} @ {event.timestamp}"
        details = {k: v for k, v in event.__dict__.items() if k != "timestamp"}
        logger.info(f"{msg} | {details}")
        print(f"    {msg}")


class AuditObserver:
    """
    Сохраняет критичные события в таблицу audit_log.
    Следит за: Enroll, Unenroll, Complete, StateChanged.
    """

    def __init__(self):
        bus = EventBus()
        bus.subscribe(EnrollEvent,       self.update)
        bus.subscribe(UnenrollEvent,     self.update)
        bus.subscribe(CompleteEvent,     self.update)
        bus.subscribe(StateChangedEvent, self.update)

    def update(self, event) -> None:
        db = DatabaseManager()
        details = str({k: v for k, v in event.__dict__.items() if k != "timestamp"})
        db.execute(
            "INSERT INTO audit_log (event_type, details, occurred_at) VALUES (?, ?, ?)",
            (event.event_type, details, event.timestamp)
        )
        logger.info(f"[AUDIT] saved {event.event_type}")


class AnalyticsObserver:
    """
    Обновляет счётчики в таблице analytics_counters при событиях.
    Следит за: Enroll, Complete, LessonAdded.
    """

    def __init__(self):
        bus = EventBus()
        bus.subscribe(EnrollEvent,     self.on_enroll)
        bus.subscribe(CompleteEvent,   self.on_complete)
        bus.subscribe(LessonAddedEvent, self.on_lesson)

    def _increment(self, key: str) -> None:
        db = DatabaseManager()
        db.execute(
            "INSERT INTO analytics_counters (key, value) VALUES (?, 1) "
            "ON CONFLICT(key) DO UPDATE SET value = value + 1",
            (key,)
        )

    def on_enroll(self, event: EnrollEvent) -> None:
        self._increment("total_enrollments")
        self._increment(f"enrollments_course_{event.course_id}")

    def on_complete(self, event: CompleteEvent) -> None:
        self._increment("total_completions")
        self._increment(f"completions_user_{event.user_id}")

    def on_lesson(self, event: LessonAddedEvent) -> None:
        self._increment("total_lessons_added")


class NotificationObserver:
    """
    Отправляет системные уведомления при ключевых событиях.
    Следит за: Complete, LessonAdded.
    Использует стратегию уведомлений из ConfigManager.
    """

    def __init__(self):
        bus = EventBus()
        bus.subscribe(CompleteEvent,    self.on_complete)
        bus.subscribe(LessonAddedEvent, self.on_lesson)

    def on_complete(self, event: CompleteEvent) -> None:
        from config import ConfigManager
        host = ConfigManager().get("email_host")
        print(f"    [NotificationObserver] Course completed by {event.user_name} "
              f"-> sending certificate via {host}")
        # Публикуем событие об отправке уведомления
        EventBus().publish(NotificationEvent(
            channel="email",
            recipient=f"{event.user_name}@system",
            message=f"Congratulations! You completed '{event.course_title}'"
        ))

    def on_lesson(self, event: LessonAddedEvent) -> None:
        print(f"    [NotificationObserver] New lesson in '{event.course_title}' "
              f"-> notifying all subscribers")
        EventBus().publish(NotificationEvent(
            channel="telegram",
            recipient="all_subscribers",
            message=f"New lesson '{event.lesson_title}' in '{event.course_title}'"
        ))
