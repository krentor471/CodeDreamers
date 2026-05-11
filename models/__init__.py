# models/__init__.py
from .user import User
from .course import Course
from .lesson import Lesson
from .lesson_progress import LessonProgress

__all__ = ['User', 'Course', 'Lesson', 'LessonProgress']