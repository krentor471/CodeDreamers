# config.py — Singleton: ConfigManager
import logging

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {
                "db_path": "codedreamers.db",
                "app_name": "CodeDreamers",
                "log_level": "INFO",
                "email_host": "smtp.example.com",
                "sms_api_key": "demo-sms-key",
                "telegram_bot_token": "demo-tg-token",
            }
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s"
            )
        return cls._instance

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value):
        self._config[key] = value
