# demo_progress.py - Демонстрация системы прохождения курса
from database import DatabaseManager
from services.progress_service import ProgressService
from patterns.command.course_commands import EnrollCommand, CommandHistory
from patterns.command.progress_commands import CompleteLessonCommand, StartCourseCommand
from models.user import User
from models.course import Course
import logging

logging.basicConfig(level=logging.INFO)

def setup_demo_data():
    """Создает тестовые данные для демонстрации"""
    db = DatabaseManager()
    
    # Создаем пользователя
    try:
        db.execute("INSERT INTO users (name, email, role) VALUES (?, ?, ?)", 
                  ("Иван Петров", "ivan@test.com", "student"))
        user_id = db.conn.lastrowid
    except:
        user = db.fetchone("SELECT id FROM users WHERE email = ?", ("ivan@test.com",))
        user_id = user["id"]
    
    # Создаем курс
    try:
        db.execute("INSERT INTO courses (title, description, price, difficulty_level, state) VALUES (?, ?, ?, ?, ?)",
                  ("Python Основы", "Изучение основ Python", 5000, "beginner", "assigned_to_user"))
        course_id = db.conn.lastrowid
    except:
        course = db.fetchone("SELECT id FROM courses WHERE title = ?", ("Python Основы",))
        course_id = course["id"]
    
    # Создаем уроки
    lessons = [
        ("Урок 1: Переменные", "Изучаем переменные в Python", 1),
        ("Урок 2: Условия", "Условные конструкции if/else", 2),
        ("Урок 3: Циклы", "Циклы for и while", 3),
        ("Урок 4: Функции", "Создание и использование функций", 4),
        ("Урок 5: Классы", "Основы ООП в Python", 5)
    ]
    
    for title, content, order_num in lessons:
        try:
            db.execute("INSERT INTO lessons (course_id, title, content, order_num) VALUES (?, ?, ?, ?)",
                      (course_id, title, content, order_num))
        except:
            pass  # Урок уже существует
    
    return user_id, course_id

def demo_course_progress():
    """Демонстрирует систему прохождения курса"""
    print("=== ДЕМОНСТРАЦИЯ СИСТЕМЫ ПРОХОЖДЕНИЯ КУРСА ===\n")
    
    # Настройка данных
    user_id, course_id = setup_demo_data()
    db = DatabaseManager()
    progress_service = ProgressService()
    history = CommandHistory()
    
    # Получаем объекты пользователя и курса
    user_row = db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
    course_row = db.fetchone("SELECT * FROM courses WHERE id = ?", (course_id,))
    
    user = User(user_row["id"], user_row["name"], user_row["email"], user_row["role"])
    course = Course(course_row["id"], course_row["title"], course_row["description"], 
                   course_row["price"], course_row["difficulty_level"])
    
    print(f"Пользователь: {user.name}")
    print(f"Курс: {course.title}")
    print()
    
    # 1. Записываемся на курс
    print("1️⃣ Записываемся на курс...")
    enroll_cmd = EnrollCommand(user, course)
    result = history.execute(enroll_cmd)
    print(f"   {result}")
    print()
    
    # 2. Начинаем прохождение курса
    print("2️⃣ Начинаем прохождение курса...")
    start_cmd = StartCourseCommand(user_id, course_id)
    result = history.execute(start_cmd)
    print(f"   {result}")
    print()
    
    # 3. Показываем начальный прогресс
    print("3️⃣ Текущий прогресс:")
    progress = progress_service.get_course_progress(user_id, course_id)
    print(f"   📊 Прогресс: {progress['completed_lessons']}/{progress['total_lessons']} уроков ({progress['progress_percentage']}%)")
    print("   📝 Уроки:")
    for lesson in progress['lessons']:
        status = "✅" if lesson['completed'] else "⏳"
        print(f"      {status} {lesson['title']}")
    print()
    
    # 4. Проходим несколько уроков
    print("4️⃣ Проходим уроки...")
    lessons = db.fetchall("SELECT id, title FROM lessons WHERE course_id = ? ORDER BY order_num LIMIT 3", (course_id,))
    
    for lesson in lessons:
        print(f"   📖 Завершаем: {lesson['title']}")
        complete_cmd = CompleteLessonCommand(user_id, lesson["id"])
        result = history.execute(complete_cmd)
        print(f"      {result}")
    print()
    
    # 5. Показываем обновленный прогресс
    print("5️⃣ Обновленный прогресс:")
    progress = progress_service.get_course_progress(user_id, course_id)
    print(f"   📊 Прогресс: {progress['completed_lessons']}/{progress['total_lessons']} уроков ({progress['progress_percentage']}%)")
    print("   📝 Уроки:")
    for lesson in progress['lessons']:
        status = "✅" if lesson['completed'] else "⏳"
        completed_info = f" (завершен {lesson['completed_at']})" if lesson['completed'] else ""
        print(f"      {status} {lesson['title']}{completed_info}")
    print()
    
    # 6. Получаем следующий урок
    next_lesson = progress_service.get_next_lesson(user_id, course_id)
    if next_lesson:
        print(f"6️⃣ Следующий урок: {next_lesson['title']}")
    else:
        print("6️⃣ Все уроки завершены!")
    print()
    
    # 7. Завершаем все оставшиеся уроки
    print("7️⃣ Завершаем оставшиеся уроки...")
    remaining_lessons = db.fetchall(
        """SELECT l.id, l.title FROM lessons l 
           LEFT JOIN lesson_progress lp ON l.id = lp.lesson_id AND lp.user_id = ?
           WHERE l.course_id = ? AND (lp.completed IS NULL OR lp.completed = 0)
           ORDER BY l.order_num""", 
        (user_id, course_id)
    )
    
    for lesson in remaining_lessons:
        print(f"   📖 Завершаем: {lesson['title']}")
        complete_cmd = CompleteLessonCommand(user_id, lesson["id"])
        result = history.execute(complete_cmd)
        print(f"      {result}")
    print()
    
    # 8. Финальный прогресс
    print("8️⃣ Финальный прогресс:")
    progress = progress_service.get_course_progress(user_id, course_id)
    print(f"   📊 Прогресс: {progress['completed_lessons']}/{progress['total_lessons']} уроков ({progress['progress_percentage']}%)")
    
    if progress['is_completed']:
        print("   🎉 КУРС ПОЛНОСТЬЮ ЗАВЕРШЕН!")
        
        # Проверяем статус записи
        enrollment = db.fetchone("SELECT status FROM enrollments WHERE user_id = ? AND course_id = ?", (user_id, course_id))
        print(f"   📋 Статус записи: {enrollment['status']}")
    print()
    
    # 9. Демонстрация UNDO
    print("9️⃣ Демонстрация отмены последнего действия...")
    undo_result = history.undo_last()
    print(f"   {undo_result}")
    
    # Показываем прогресс после отмены
    progress = progress_service.get_course_progress(user_id, course_id)
    print(f"   📊 Прогресс после отмены: {progress['completed_lessons']}/{progress['total_lessons']} уроков ({progress['progress_percentage']}%)")

if __name__ == "__main__":
    demo_course_progress()