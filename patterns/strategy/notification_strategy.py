# patterns/strategy/notification_strategy.py — Strategy Pattern
#
# Стратегии — полноценные части системы:
#   - читают настройки из ConfigManager (хост, токены, ключи)
#   - сохраняют каждое уведомление в таблицу notifications (БД)
#   - имитируют реальную отправку через соответствующий канал

import logging
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


def _save_to_db(channel: str, recipient: str, message: str) -> None:
    """Сохраняет факт отправки уведомления в БД."""
    # Импорт здесь чтобы избежать циклических зависимостей
    from database import DatabaseManager
    db = DatabaseManager()
    db.execute(
        "INSERT INTO notifications (channel, recipient, message, sent_at) VALUES (?, ?, ?, ?)",
        (channel, recipient, message, datetime.now().isoformat())
    )


class NotificationStrategy(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str) -> None:
        pass

    @property
    @abstractmethod
    def channel_name(self) -> str:
        pass


class EmailNotification(NotificationStrategy):
    """
    Отправка через Email.
    Использует email_host из ConfigManager.
    """
    @property
    def channel_name(self) -> str:
        return "email"

    def send(self, recipient: str, message: str) -> None:
        from config import ConfigManager
        host = ConfigManager().get("email_host")
        logger.info(f"[EMAIL] via {host} -> {recipient}: {message}")
        print(f"    [Email] via {host} | to: {recipient} | msg: {message}")
        _save_to_db("email", recipient, message)


class SMSNotification(NotificationStrategy):
    """
    Отправка через SMS.
    Использует sms_api_key из ConfigManager.
    """
    @property
    def channel_name(self) -> str:
        return "sms"

    def send(self, recipient: str, message: str) -> None:
        from config import ConfigManager
        api_key = ConfigManager().get("sms_api_key")
        logger.info(f"[SMS] api_key={api_key} -> {recipient}: {message}")
        print(f"    [SMS] api_key={api_key} | to: {recipient} | msg: {message}")
        _save_to_db("sms", recipient, message)


class TelegramNotification(NotificationStrategy):
    """
    Отправка через Telegram Bot.
    Использует telegram_bot_token из ConfigManager.
    """
    @property
    def channel_name(self) -> str:
        return "telegram"

    def send(self, recipient: str, message: str) -> None:
        from config import ConfigManager
        token = ConfigManager().get("telegram_bot_token")
        logger.info(f"[Telegram] bot={token} -> {recipient}: {message}")
        print(f"    [Telegram] bot={token} | to: {recipient} | msg: {message}")
        _save_to_db("telegram", recipient, message)


# Стратегия по умолчанию для каждой роли пользователя
DEFAULT_STRATEGY: dict[str, NotificationStrategy] = {
    "student": EmailNotification(),
    "mentor":  TelegramNotification(),
    "admin":   SMSNotification(),
}
