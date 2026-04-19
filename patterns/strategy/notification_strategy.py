# patterns/strategy/notification_strategy.py — Strategy Pattern
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class NotificationStrategy(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str) -> None:
        pass

class EmailNotification(NotificationStrategy):
    def send(self, recipient: str, message: str) -> None:
        logger.info(f"[EMAIL] -> {recipient}: {message}")
        print(f"    [Email] to {recipient}: {message}")

class SMSNotification(NotificationStrategy):
    def send(self, recipient: str, message: str) -> None:
        logger.info(f"[SMS] -> {recipient}: {message}")
        print(f"    [SMS] to {recipient}: {message}")

class TelegramNotification(NotificationStrategy):
    def send(self, recipient: str, message: str) -> None:
        logger.info(f"[Telegram] -> {recipient}: {message}")
        print(f"    [Telegram] to {recipient}: {message}")
