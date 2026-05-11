# services/discipline_service.py
from database import DatabaseManager
from typing import List, Dict

class DisciplineService:
    def __init__(self):
        self.db = DatabaseManager()
    
    def create_discipline(self, title: str, description: str = "", content: str = "") -> int:
        cursor = self.db.execute(
            "INSERT INTO disciplines (title, description, content) VALUES (?, ?, ?)",
            (title, description, content)
        )
        return cursor.lastrowid
    
    def get_all_disciplines(self) -> List[Dict]:
        rows = self.db.fetchall("SELECT * FROM disciplines ORDER BY title")
        return [dict(row) for row in rows]
    
    def get_discipline(self, discipline_id: int) -> Dict:
        row = self.db.fetchone("SELECT * FROM disciplines WHERE id = ?", (discipline_id,))
        return dict(row) if row else None
    
    def update_discipline(self, discipline_id: int, title: str, description: str, content: str):
        self.db.execute(
            "UPDATE disciplines SET title = ?, description = ?, content = ? WHERE id = ?",
            (title, description, content, discipline_id)
        )
    
    def delete_discipline(self, discipline_id: int):
        self.db.execute("DELETE FROM module_disciplines WHERE discipline_id = ?", (discipline_id,))
        self.db.execute("DELETE FROM lessons WHERE discipline_id = ?", (discipline_id,))
        self.db.execute("DELETE FROM disciplines WHERE id = ?", (discipline_id,))
    
    def add_lesson_to_discipline(self, discipline_id: int, title: str, content: str, order_num: int) -> int:
        cursor = self.db.execute(
            "INSERT INTO lessons (discipline_id, title, content, order_num, course_id) VALUES (?, ?, ?, ?, 0)",
            (discipline_id, title, content, order_num)
        )
        return cursor.lastrowid
    
    def get_discipline_lessons(self, discipline_id: int) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM lessons WHERE discipline_id = ? ORDER BY order_num",
            (discipline_id,)
        )
        return [dict(row) for row in rows]
    
    def delete_lesson(self, lesson_id: int):
        self.db.execute("DELETE FROM lesson_progress WHERE lesson_id = ?", (lesson_id,))
        self.db.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
