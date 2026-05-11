# database.py — Singleton: DatabaseManager
import sqlite3
import logging
from config import ConfigManager

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            db_path = ConfigManager().get("db_path")
            cls._instance._conn = sqlite3.connect(db_path, check_same_thread=False)
            cls._instance._conn.row_factory = sqlite3.Row
            logger.info(f"Database connected: {db_path}")
            cls._instance._init_tables()
            cls._instance._migrate()
        return cls._instance

    def _init_tables(self):
        cursor = self._conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                difficulty_level TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                order_num INTEGER NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                completed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                UNIQUE(user_id, course_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );
            CREATE TABLE IF NOT EXISTS course_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                UNIQUE(course_id, tag),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS course_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                options TEXT NOT NULL,
                final_price REAL NOT NULL,
                description TEXT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analytics_counters (
                key TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            );
        """)
        self._conn.commit()
        logger.info("Tables initialized")

    def _migrate(self):
        """Safe migration — добавляет новые колонки и таблицы если их ещё нет."""
        migrations = [
            "ALTER TABLE courses ADD COLUMN state TEXT DEFAULT 'new'",
            "ALTER TABLE lessons ADD COLUMN module_id INTEGER REFERENCES modules(id)",
            "ALTER TABLE lessons ADD COLUMN discipline_id INTEGER REFERENCES disciplines(id)",
        ]
        for sql in migrations:
            try:
                self._conn.execute(sql)
                self._conn.commit()
            except Exception:
                pass

        # Таблицы модулей и дисциплин через migrate (не перезаписывают существующие)
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS modules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id   INTEGER NOT NULL REFERENCES courses(id),
                title       TEXT    NOT NULL,
                order_num   INTEGER NOT NULL DEFAULT 1,
                teacher_id  INTEGER REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS disciplines (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT,
                content     TEXT
            );
            CREATE TABLE IF NOT EXISTS module_disciplines (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id     INTEGER NOT NULL REFERENCES modules(id),
                discipline_id INTEGER NOT NULL REFERENCES disciplines(id),
                order_num     INTEGER NOT NULL DEFAULT 1,
                UNIQUE(module_id, discipline_id)
            );
            CREATE TABLE IF NOT EXISTS lesson_progress (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                lesson_id   INTEGER NOT NULL REFERENCES lessons(id),
                completed   INTEGER DEFAULT 0,
                completed_at TEXT,
                UNIQUE(user_id, lesson_id)
            );
        """)
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def execute(self, sql: str, params: tuple = ()):
        cursor = self._conn.cursor()
        cursor.execute(sql, params)
        self._conn.commit()
        return cursor

    def fetchall(self, sql: str, params: tuple = ()):
        return self._conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()):
        return self._conn.execute(sql, params).fetchone()
