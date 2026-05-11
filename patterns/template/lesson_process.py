# patterns/template/lesson_process.py — Template Method по BPMN
#
# BaseLessonProcess.execute() — шаблонный метод, фиксирует порядок шагов BPMN:
#   register → test → validate → offer → choose → start_lesson →
#   loop(complete_module → check_by_teacher) → comment → save
#
# Делегирование субклассирования:
#   check_module_by_teacher() — абстрактный, каждый подкласс реализует по-своему
#   CourseProcessFactory      — делегирует создание нужного подкласса

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from database import DatabaseManager

logger = logging.getLogger(__name__)


class BaseLessonProcess(ABC):
    """
    Шаблонный метод учебного процесса.
    Подклассы переопределяют только check_module_by_teacher().
    """

    def __init__(self, user_id: int, course_id: int):
        self.user_id = user_id
        self.course_id = course_id
        self.db = DatabaseManager()
        self._module_status: str = "pending"
        self._comment: str = ""

    # ── ШАБЛОННЫЙ МЕТОД ───────────────────────────────────────────────────

    def execute(self) -> dict:
        """Весь процесс по BPMN. Не переопределяется в подклассах."""
        log = []

        log.append(self.register_student())
        log.append(self.test_knowledge())

        if not self.validate_data():
            log.append(self.fix_errors())
            return {"status": "error", "log": log}

        log.append(self.make_personal_offer())
        log.append(self.choose_course())
        log.append(self.start_first_lesson())

        # Цикл: завершить модуль → проверка преподавателем → доработка если нужно
        attempts = 0
        while True:
            attempts += 1
            log.append(self.complete_module())
            log.append(self.create_enrollment())
            log.append(self.load_modules())

            passed = self.check_module_by_teacher()
            if passed:
                log.append(self.fix_module_status("passed"))
                break
            else:
                log.append(self.request_rework(attempts))
                if attempts >= 3:
                    log.append(self.fix_module_status("failed"))
                    break

        log.append(self.leave_comment())
        log.append(self.save_comment())

        logger.info(f"LessonProcess done: user={self.user_id} course={self.course_id} "
                    f"status={self._module_status} attempts={attempts}")
        return {"status": self._module_status, "attempts": attempts, "log": log}

    # ── ШАГИ (можно переопределять в подклассах как хуки) ─────────────────

    def register_student(self) -> str:
        row = self.db.fetchone("SELECT name FROM users WHERE id = ?", (self.user_id,))
        name = row["name"] if row else f"user#{self.user_id}"
        return f"[1] Студент '{name}' вошёл на платформу"

    def test_knowledge(self) -> str:
        return "[2] Пройден тест на уровень знаний"

    def validate_data(self) -> bool:
        row = self.db.fetchone(
            "SELECT id FROM enrollments WHERE user_id=? AND course_id=?",
            (self.user_id, self.course_id)
        )
        valid = row is None  # не записан повторно
        logger.info(f"validate_data: user={self.user_id} course={self.course_id} valid={valid}")
        return valid

    def fix_errors(self) -> str:
        return "[3] Ошибка: студент уже записан на этот курс"

    def make_personal_offer(self) -> str:
        row = self.db.fetchone(
            "SELECT title, difficulty_level FROM courses WHERE id = ?", (self.course_id,)
        )
        title = row["title"] if row else f"course#{self.course_id}"
        level = row["difficulty_level"] if row else "?"
        return f"[4] Сформировано персональное предложение: '{title}' [{level}]"

    def choose_course(self) -> str:
        return f"[5] Студент выбрал курс id={self.course_id}"

    def start_first_lesson(self) -> str:
        row = self.db.fetchone(
            "SELECT title FROM lessons WHERE course_id=? ORDER BY order_num LIMIT 1",
            (self.course_id,)
        )
        title = row["title"] if row else "перший урок"
        return f"[6] Начат первый урок: '{title}'"

    def complete_module(self) -> str:
        return "[7] Студент завершил модуль"

    def create_enrollment(self) -> str:
        try:
            self.db.execute(
                "INSERT INTO enrollments (user_id, course_id, status) VALUES (?, ?, 'active')",
                (self.user_id, self.course_id)
            )
            return "[8] Enrollment создан (БД)"
        except Exception:
            return "[8] Enrollment уже существует (БД)"

    def load_modules(self) -> str:
        count = self.db.fetchone(
            "SELECT COUNT(*) as n FROM lessons WHERE course_id=?", (self.course_id,)
        )["n"]
        return f"[9] Загружено {count} уроков (Module/SubModule)"

    # ── АБСТРАКТНИЙ КРОК — делегування субклассуванню ─────────────────────

    @abstractmethod
    def check_module_by_teacher(self) -> bool:
        """
        Перевірка роботи викладачем.
        Кожен підклас реалізує свою логіку перевірки.
        Повертає True (зараховано) або False (на доопрацювання).
        """
        pass

    # ── ХУКИ ──────────────────────────────────────────────────────────────

    def request_rework(self, attempt: int) -> str:
        return f"[10] Запрос на доработку (попытка {attempt}) → возврат к модулю"

    def fix_module_status(self, status: str) -> str:
        self._module_status = status
        self.db.execute(
            "UPDATE enrollments SET status=?, completed=? WHERE user_id=? AND course_id=?",
            (status, 1 if status == "passed" else 0, self.user_id, self.course_id)
        )
        return f"[11] Статус модуля зафиксирован: '{status}' (БД)"

    def leave_comment(self) -> str:
        self._comment = f"Курс пройден со статусом: {self._module_status}"
        return f"[12] Студент оставил комментарий"

    def save_comment(self) -> str:
        self.db.execute(
            "INSERT INTO notifications (channel, recipient, message, sent_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            ("comment", str(self.user_id), self._comment)
        )
        return "[13] Комментарий сохранён в БД ✅"


# ── КОНКРЕТНІ ПІДКЛАСИ (делегування субклассування) ───────────────────────

class PythonLessonProcess(BaseLessonProcess):
    """Курс Python: перевірка коду викладачем — завжди зараховується."""

    def check_module_by_teacher(self) -> bool:
        logger.info(f"[Python] Викладач перевіряє Python-код user={self.user_id}")
        return True


class MathLessonProcess(BaseLessonProcess):
    """Курс математики: автоперевірка — зараховується з 2-ї спроби."""

    def __init__(self, user_id: int, course_id: int):
        super().__init__(user_id, course_id)
        self._attempt = 0

    def check_module_by_teacher(self) -> bool:
        self._attempt += 1
        passed = self._attempt >= 2
        logger.info(f"[Math] Автоперевірка спроба={self._attempt} passed={passed}")
        return passed


class WebLessonProcess(BaseLessonProcess):
    """Веб-курс: перевірка через peer-review — зараховується з першого разу."""

    def check_module_by_teacher(self) -> bool:
        logger.info(f"[Web] Peer-review user={self.user_id}")
        return True


# ── ФАБРИКА / ДЕЛЕГАТОР ───────────────────────────────────────────────────

_PROCESS_MAP: dict[str, type] = {
    "python":     PythonLessonProcess,
    "math":       MathLessonProcess,
    "web":        WebLessonProcess,
    "basic":      PythonLessonProcess,   # fallback для basic-курсів
    "advanced":   WebLessonProcess,
    "professional": MathLessonProcess,
}


class CourseProcessFactory:
    """
    Делегує виконання процесу потрібному підкласу
    на основі difficulty_level курсу з БД.
    """

    @staticmethod
    def run(user_id: int, course_id: int) -> dict:
        db = DatabaseManager()
        row = db.fetchone(
            "SELECT difficulty_level FROM courses WHERE id = ?", (course_id,)
        )
        level = row["difficulty_level"] if row else "basic"
        cls = _PROCESS_MAP.get(level, PythonLessonProcess)
        logger.info(f"CourseProcessFactory: level='{level}' -> {cls.__name__}")
        return cls(user_id, course_id).execute()
