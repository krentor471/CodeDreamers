# models/lesson_progress.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class LessonProgress:
    id: int
    user_id: int
    lesson_id: int
    completed: bool = False
    completed_at: Optional[datetime] = None
    
    def mark_completed(self):
        self.completed = True
        self.completed_at = datetime.now()