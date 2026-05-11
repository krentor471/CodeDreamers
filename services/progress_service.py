# services/progress_service.py
from typing import List, Dict
from database import DatabaseManager
from models.lesson_progress import LessonProgress
from patterns.state.enrollment_state import EnrollmentContext
from patterns.state.course_state import CourseContext
from patterns.observer.event_bus import EventBus, LessonCompletedEvent
import logging

logger = logging.getLogger(__name__)

class ProgressService:
    def __init__(self):
        self.db = DatabaseManager()
    
    def complete_lesson(self, user_id: int, lesson_id: int) -> str:
        """Отмечает урок как пройденный"""
        try:
            # Проверяем, есть ли уже запись о прогрессе
            existing = self.db.fetchone(
                "SELECT id FROM lesson_progress WHERE user_id = ? AND lesson_id = ?",
                (user_id, lesson_id)
            )
            
            if existing:
                self.db.execute(
                    "UPDATE lesson_progress SET completed = 1, completed_at = datetime('now') WHERE user_id = ? AND lesson_id = ?",
                    (user_id, lesson_id)
                )
            else:
                self.db.execute(
                    "INSERT INTO lesson_progress (user_id, lesson_id, completed, completed_at) VALUES (?, ?, 1, datetime('now'))",
                    (user_id, lesson_id)
                )
            
            # Получаем информацию об уроке
            lesson_info = self.db.fetchone(
                "SELECT l.title, l.course_id FROM lessons l WHERE l.id = ?",
                (lesson_id,)
            )
            
            if lesson_info:
                # Публикуем событие
                EventBus().publish(LessonCompletedEvent(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    lesson_title=lesson_info["title"],
                    course_id=lesson_info["course_id"]
                ))
                
                # Проверяем, завершен ли весь курс
                self._check_course_completion(user_id, lesson_info["course_id"])
                
                return f"Урок '{lesson_info['title']}' отмечен как пройденный"
            
            return "Урок отмечен как пройденный"
            
        except Exception as e:
            logger.error(f"Ошибка при завершении урока: {e}")
            return f"Ошибка: {e}"
    
    def get_course_progress(self, user_id: int, course_id: int) -> Dict:
        """Возвращает прогресс пользователя по курсу"""
        # Получаем все уроки курса
        lessons = self.db.fetchall(
            "SELECT id, title, order_num FROM lessons WHERE course_id = ? ORDER BY order_num",
            (course_id,)
        )
        
        # Получаем прогресс по урокам
        progress = self.db.fetchall(
            """SELECT lp.lesson_id, lp.completed, lp.completed_at 
               FROM lesson_progress lp 
               JOIN lessons l ON lp.lesson_id = l.id 
               WHERE lp.user_id = ? AND l.course_id = ?""",
            (user_id, course_id)
        )
        
        progress_dict = {p["lesson_id"]: p for p in progress}
        
        lesson_list = []
        completed_count = 0
        
        for lesson in lessons:
            lesson_progress = progress_dict.get(lesson["id"])
            is_completed = lesson_progress and lesson_progress["completed"]
            
            lesson_list.append({
                "id": lesson["id"],
                "title": lesson["title"],
                "order_num": lesson["order_num"],
                "completed": bool(is_completed),
                "completed_at": lesson_progress["completed_at"] if lesson_progress else None
            })
            
            if is_completed:
                completed_count += 1
        
        total_lessons = len(lessons)
        progress_percentage = (completed_count / total_lessons * 100) if total_lessons > 0 else 0
        
        return {
            "course_id": course_id,
            "total_lessons": total_lessons,
            "completed_lessons": completed_count,
            "progress_percentage": round(progress_percentage, 1),
            "lessons": lesson_list,
            "is_completed": completed_count == total_lessons and total_lessons > 0
        }
    
    def _check_course_completion(self, user_id: int, course_id: int):
        """Проверяет, завершен ли курс полностью"""
        progress = self.get_course_progress(user_id, course_id)
        
        if progress["is_completed"]:
            # Получаем информацию о пользователе и курсе
            user_info = self.db.fetchone("SELECT name FROM users WHERE id = ?", (user_id,))
            course_info = self.db.fetchone("SELECT title FROM courses WHERE id = ?", (course_id,))
            
            if user_info and course_info:
                # Обновляем состояние записи на курс
                ctx = EnrollmentContext.load(
                    user_id, course_id,
                    user_info["name"], course_info["title"]
                )
                result = ctx.complete()
                logger.info(f"Курс автоматически завершен: {result}")
    
    def get_next_lesson(self, user_id: int, course_id: int) -> Dict:
        """Возвращает следующий незавершенный урок"""
        progress = self.get_course_progress(user_id, course_id)
        
        for lesson in progress["lessons"]:
            if not lesson["completed"]:
                return lesson
        
        return None  # Все уроки завершены