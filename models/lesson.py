# models/lesson.py
from dataclasses import dataclass

@dataclass
class Lesson:
    id: int
    course_id: int
    title: str
    content: str
    order_num: int

    def __str__(self):
        return f"Lesson {self.order_num}: {self.title}"
