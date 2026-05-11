# patterns/command/progress_commands.py
from abc import ABC, abstractmethod
from services.progress_service import ProgressService
from patterns.command.course_commands import Command
import logging

logger = logging.getLogger(__name__)

class CompleteLessonCommand(Command):
    """Команда для завершения урока"""
    
    def __init__(self, user_id: int, lesson_id: int):
        self.user_id = user_id
        self.lesson_id = lesson_id
        self.progress_service = ProgressService()
        self._was_completed = False
    
    def execute(self) -> str:
        # Проверяем текущий статус перед выполнением
        from database import DatabaseManager
        db = DatabaseManager()
        existing = db.fetchone(
            "SELECT completed FROM lesson_progress WHERE user_id = ? AND lesson_id = ?",
            (self.user_id, self.lesson_id)
        )
        self._was_completed = existing and existing["completed"]
        
        return self.progress_service.complete_lesson(self.user_id, self.lesson_id)
    
    def undo(self) -> str:
        if self._was_completed:
            return f"UNDO: урок уже был завершен ранее"
        
        from database import DatabaseManager
        db = DatabaseManager()
        db.execute(
            "UPDATE lesson_progress SET completed = 0, completed_at = NULL WHERE user_id = ? AND lesson_id = ?",
            (self.user_id, self.lesson_id)
        )
        return f"UNDO: урок отмечен как незавершенный"


class StartCourseCommand(Command):
    """Команда для начала прохождения курса"""
    
    def __init__(self, user_id: int, course_id: int):
        self.user_id = user_id
        self.course_id = course_id
        self.progress_service = ProgressService()
    
    def execute(self) -> str:
        from database import DatabaseManager
        from patterns.state.course_state import CourseContext
        
        db = DatabaseManager()
        
        # Проверяем, записан ли пользователь на курс
        enrollment = db.fetchone(
            "SELECT status FROM enrollments WHERE user_id = ? AND course_id = ?",
            (self.user_id, self.course_id)
        )
        
        if not enrollment:
            return "Ошибка: пользователь не записан на курс"
        
        if enrollment["status"] != "active":
            return f"Ошибка: статус записи '{enrollment['status']}', нужен 'active'"
        
        # Обновляем состояние курса на "в процессе"
        course_ctx = CourseContext.load(self.course_id)
        result = course_ctx.start_progress()
        
        # Получаем первый урок
        next_lesson = self.progress_service.get_next_lesson(self.user_id, self.course_id)
        
        if next_lesson:
            return f"{result}. Следующий урок: {next_lesson['title']}"
        else:
            return f"{result}. Нет доступных уроков"
    
    def undo(self) -> str:
        # Возвращаем курс в состояние "назначен пользователю"
        from patterns.state.course_state import CourseContext, AssignedToUserState
        
        course_ctx = CourseContext.load(self.course_id)
        course_ctx.state = AssignedToUserState()
        course_ctx._save()
        
        return "UNDO: курс возвращен в состояние 'назначен пользователю'"