# main.py — CodeDreamers: демонстрация всех паттернов + рекомендательная система
import os
import sys
import logging

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

if os.path.exists("codedreamers.db"):
    os.remove("codedreamers.db")

from config import ConfigManager
from database import DatabaseManager
from patterns.factory.user_factory import UserFactory
from patterns.factory.course_factory import CourseFactory
from patterns.decorator.course_decorator import WithCertificate, WithMentorSupport, WithLifetimeAccess
from patterns.command.course_commands import EnrollCommand, CompleteCourseCommand, CommandHistory
from patterns.strategy.notification_strategy import EmailNotification, SMSNotification, TelegramNotification
from services.student_observer import StudentObserver
from services.recommendation_service import recommend_courses
from seed import seed

logger = logging.getLogger(__name__)

def separator(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)

def main():
    # -- 1. Singleton --------------------------------------------------
    separator("1. SINGLETON — Config & Database")
    cfg = ConfigManager()
    cfg2 = ConfigManager()
    print(f"  ConfigManager singleton: {cfg is cfg2}")
    print(f"  App: {cfg.get('app_name')}, DB: {cfg.get('db_path')}")
    db = DatabaseManager()
    db2 = DatabaseManager()
    print(f"  DatabaseManager singleton: {db is db2}")

    # -- 2. SEED — заполняем БД тестовыми данными ---------------------
    separator("2. SEED — Заполнение БД")
    counts = seed()
    print(f"  users:       {counts['users']}")
    print(f"  courses:     {counts['courses']}")
    print(f"  lessons:     {counts['lessons']}")
    print(f"  enrollments: {counts['enrollments']}")
    print(f"  tags:        {counts['tags']}")
    print(f"  TOTAL:       {sum(counts.values())} records")

    # Получаем объекты из БД для демонстрации паттернов
    separator("3. FACTORY — Объекты для демонстрации паттернов")
    student = UserFactory.create("Demo Student", "demo@example.com", "student")
    c1_row = db.fetchone("SELECT * FROM courses WHERE title='Python Basics'")
    c4_row = db.fetchone("SELECT * FROM courses WHERE title='Algorithms'")
    from models.course import Course
    c1 = Course(id=c1_row["id"], title=c1_row["title"], description=c1_row["description"],
                price=c1_row["price"], difficulty_level=c1_row["difficulty_level"])
    c4 = Course(id=c4_row["id"], title=c4_row["title"], description=c4_row["description"],
                price=c4_row["price"], difficulty_level=c4_row["difficulty_level"])
    print(f"  Demo user: {student}")
    print(f"  Working with: '{c1.title}', '{c4.title}'")

    # -- 4. Decorator --------------------------------------------------
    separator("4. DECORATOR — Добавляем опции к курсу")
    decorated = WithCertificate(WithMentorSupport(c1))
    print(f"  Base:          ${c1.get_price():.2f}")
    print(f"  + MentorSupport + Certificate: ${decorated.get_price():.2f}")
    print(f"  Description: {decorated.get_description()}")

    # -- 5. Observer ---------------------------------------------------
    separator("5. OBSERVER — Подписка на обновления курса")
    alice_observer = StudentObserver(student)
    c1.subscribe(alice_observer)
    print(f"  {student.name} subscribed to '{c1.title}'")

    # -- 6. Strategy ---------------------------------------------------
    separator("6. STRATEGY — Уведомления")
    print("  Default (Email):")
    student.notify("Welcome to CodeDreamers!")
    student.set_notification_strategy(SMSNotification())
    print("  Switched to SMS:")
    student.notify("Your course is ready!")
    student.set_notification_strategy(TelegramNotification())
    print("  Switched to Telegram:")
    student.notify("New lesson available!")
    student.set_notification_strategy(EmailNotification())

    # -- 7. Command — Demo Student записывается и завершает курсы -----
    separator("7. COMMAND — Операции с курсом")
    history = CommandHistory()

    history.execute(EnrollCommand(student, c1))
    history.execute(CompleteCourseCommand(student, c1))
    history.execute(EnrollCommand(student, c4))
    history.execute(CompleteCourseCommand(student, c4))
    print(f"  [OK] {student.name} completed: '{c1.title}', '{c4.title}'")

    result = history.undo_last()
    print(f"  [UNDO] {result}")
    result = history.undo_last()
    print(f"  [UNDO] {result}")

    # Восстанавливаем для рекомендаций
    history.execute(EnrollCommand(student, c4))
    history.execute(CompleteCourseCommand(student, c4))

    # -- 8. Observer + Strategy ----------------------------------------
    separator("8. OBSERVER + STRATEGY — Новый урок -> уведомление")
    c1.add_lesson("Variables and Data Types")

    # -- 9. РЕКОМЕНДАТЕЛЬНАЯ СИСТЕМА -----------------------------------
    separator("9. RECOMMENDATION — Косинусное сходство")
    print(f"  Профиль {student.name}: завершил '{c1.title}' и '{c4.title}'")
    print()

    recommendations = recommend_courses(user_id=student.id, top_n=3)
    print("  Рекомендации (косинусное сходство с профилем):")
    print(f"  {'Курс':<25} {'Теги':<30} {'Сходство':>10}")
    print(f"  {'-'*25} {'-'*30} {'-'*10}")
    for rec in recommendations:
        tags_str = ", ".join(rec["tags"])
        print(f"  {rec['title']:<25} {tags_str:<30} {rec['similarity']:>10.4f}")

    # -- Итог из БД ----------------------------------------------------
    separator("ИТОГ — Данные в БД")

    users = db.fetchall("SELECT * FROM users")
    print(f"  Users ({len(users)}):")
    for u in users:
        print(f"    [{u['id']}] {u['name']:<15} — {u['role']}")

    courses = db.fetchall("SELECT * FROM courses")
    print(f"\n  Courses ({len(courses)}):")
    for c in courses:
        tags = db.fetchall("SELECT tag FROM course_tags WHERE course_id=?", (c['id'],))
        tags_str = ", ".join(t['tag'] for t in tags)
        print(f"    [{c['id']}] {c['title']:<25} ${c['price']:<8.2f} [{c['difficulty_level']}]")
        print(f"         tags: {tags_str}")

    lessons = db.fetchall("SELECT l.*, c.title as course_title FROM lessons l JOIN courses c ON l.course_id=c.id ORDER BY l.course_id, l.order_num")
    print(f"\n  Lessons ({len(lessons)}):")
    for l in lessons:
        print(f"    [{l['id']}] {l['course_title']:<25} #{l['order_num']} {l['title']}")

    enrollments = db.fetchall("""
        SELECT e.*, u.name as uname, c.title as ctitle
        FROM enrollments e
        JOIN users u ON e.user_id=u.id
        JOIN courses c ON e.course_id=c.id
        ORDER BY e.user_id
    """)
    print(f"\n  Enrollments ({len(enrollments)}):")
    for e in enrollments:
        status = "completed" if e['completed'] else "active"
        print(f"    [{e['id']}] {e['uname']:<15} -> {e['ctitle']:<25} [{status}]")

    total = (db.fetchone("SELECT COUNT(*) as n FROM users")["n"] +
             db.fetchone("SELECT COUNT(*) as n FROM courses")["n"] +
             db.fetchone("SELECT COUNT(*) as n FROM lessons")["n"] +
             db.fetchone("SELECT COUNT(*) as n FROM enrollments")["n"] +
             db.fetchone("SELECT COUNT(*) as n FROM course_tags")["n"])
    print(f"\n  TOTAL records in DB: {total}")
    print("\n  Все паттерны + рекомендательная система успешно продемонстрированы!\n")

if __name__ == "__main__":
    main()
