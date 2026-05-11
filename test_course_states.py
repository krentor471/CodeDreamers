# test_course_states.py — Тест паттерна State для курсов

from patterns.state.course_state import CourseContext, _STATE_MAP
from database import DatabaseManager

def test_course_states():
    """Тестирует переходы состояний курса"""
    
    # Создаем тестовый курс
    db = DatabaseManager()
    cursor = db.execute(
        "INSERT INTO courses (title, description, price, difficulty_level, state) VALUES (?, ?, ?, ?, ?)",
        ("Тестовый курс", "Описание", 100.0, "basic", "new")
    )
    course_id = cursor.lastrowid
    
    print(f"Создан курс с ID: {course_id}")
    
    # Загружаем контекст
    ctx = CourseContext.load(course_id)
    print(f"Начальное состояние: {ctx.status} ({ctx.state.display_name})")
    
    # Тестируем переходы
    print("\n=== Тестирование переходов ===")
    
    # new -> assigned_to_mentor
    result = ctx.assign_mentor()
    print(f"1. {result}")
    print(f"   Состояние: {ctx.status} ({ctx.state.display_name}) - цвет: {ctx.state.color}")
    
    # assigned_to_mentor -> assigned_to_user  
    result = ctx.assign_user()
    print(f"2. {result}")
    print(f"   Состояние: {ctx.status} ({ctx.state.display_name}) - цвет: {ctx.state.color}")
    
    # assigned_to_user -> in_progress
    result = ctx.start_progress()
    print(f"3. {result}")
    print(f"   Состояние: {ctx.status} ({ctx.state.display_name}) - цвет: {ctx.state.color}")
    
    # in_progress -> completed
    result = ctx.complete()
    print(f"4. {result}")
    print(f"   Состояние: {ctx.status} ({ctx.state.display_name}) - цвет: {ctx.state.color}")
    
    print("\n=== Тестирование недопустимых переходов ===")
    
    # Попытка выполнить недопустимый переход
    result = ctx.assign_mentor()  # из completed нельзя назначить ментора
    print(f"5. {result}")
    
    # Очистка
    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    print(f"\nТестовый курс удален")

def test_state_info():
    """Тестирует информацию о состояниях"""
    print("\n=== Информация о состояниях ===")
    
    for state_name, state_obj in _STATE_MAP.items():
        print(f"{state_name:20} | {state_obj.display_name:20} | {state_obj.color}")

if __name__ == "__main__":
    test_course_states()
    test_state_info()