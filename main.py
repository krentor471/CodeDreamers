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

    # -- 2. Factory — создаём пользователей и курсы с тегами ----------
    separator("2. FACTORY — Создание пользователей и курсов")
    student = UserFactory.create("Alice", "alice@example.com", "student")
    mentor  = UserFactory.create("Bob",   "bob@example.com",   "mentor")
    admin   = UserFactory.create("Carol", "carol@example.com", "admin")
    print(f"  {student}")
    print(f"  {mentor}")
    print(f"  {admin}")

    # Создаём 5 курсов с тегами для работы рекомендательной системы
    c1 = CourseFactory.create("Python Basics",      "Intro to Python",          100.0, "basic",
                              tags=["python", "programming", "beginner"])
    c2 = CourseFactory.create("Python Advanced",    "OOP, decorators, async",   100.0, "advanced",
                              tags=["python", "programming", "oop"])
    c3 = CourseFactory.create("Web with Django",    "Build web apps",           100.0, "advanced",
                              tags=["python", "web", "django"])
    c4 = CourseFactory.create("Algorithms",         "Sorting, graphs, DP",      100.0, "professional",
                              tags=["algorithms", "programming", "math"])
    c5 = CourseFactory.create("Data Science",       "Pandas, ML basics",        100.0, "professional",
                              tags=["python", "math", "data", "ml"])

    print(f"\n  Courses created: {c1.title}, {c2.title}, {c3.title}, {c4.title}, {c5.title}")

    # -- 3. Decorator --------------------------------------------------
    separator("3. DECORATOR — Добавляем опции к курсу")
    decorated = WithCertificate(WithMentorSupport(c1))
    print(f"  Base:          ${c1.get_price():.2f}")
    print(f"  + MentorSupport + Certificate: ${decorated.get_price():.2f}")
    print(f"  Description: {decorated.get_description()}")

    # -- 4. Observer ---------------------------------------------------
    separator("4. OBSERVER — Подписка на обновления курса")
    alice_observer = StudentObserver(student)
    c1.subscribe(alice_observer)
    print(f"  {student.name} subscribed to '{c1.title}'")

    # -- 5. Strategy ---------------------------------------------------
    separator("5. STRATEGY — Уведомления")
    print("  Default (Email):")
    student.notify("Welcome to CodeDreamers!")
    student.set_notification_strategy(SMSNotification())
    print("  Switched to SMS:")
    student.notify("Your course is ready!")
    student.set_notification_strategy(TelegramNotification())
    print("  Switched to Telegram:")
    student.notify("New lesson available!")
    student.set_notification_strategy(EmailNotification())

    # -- 6. Command — Alice записывается и завершает c1, c4 -----------
    separator("6. COMMAND — Операции с курсом")
    history = CommandHistory()

    print("  Alice enrolls and completes Python Basics and Algorithms:")
    history.execute(EnrollCommand(student, c1))
    history.execute(CompleteCourseCommand(student, c1))   # completed=1, вес x2 в профиле
    history.execute(EnrollCommand(student, c4))
    history.execute(CompleteCourseCommand(student, c4))   # completed=1, вес x2 в профиле
    print(f"  [OK] Alice completed: '{c1.title}', '{c4.title}'")

    result = history.undo_last()
    print(f"  [UNDO] {result}")
    result = history.undo_last()
    print(f"  [UNDO] {result}")

    # Восстанавливаем записи для рекомендаций
    history.execute(EnrollCommand(student, c4))
    history.execute(CompleteCourseCommand(student, c4))

    # -- 7. Observer + Strategy ----------------------------------------
    separator("7. OBSERVER + STRATEGY — Новый урок -> уведомление")
    c1.add_lesson("Variables and Data Types")

    # -- 8. РЕКОМЕНДАТЕЛЬНАЯ СИСТЕМА -----------------------------------
    separator("8. RECOMMENDATION — Косинусное сходство")

    print("  Профиль Alice (пройденные курсы):")
    print(f"    - '{c1.title}' [completed] tags: python, programming, beginner")
    print(f"    - '{c4.title}' [completed] tags: algorithms, programming, math")
    print()
    print("  Вектор профиля Alice (сумма тегов с весом 2 за completed):")
    print("    python=2, programming=4, beginner=2, algorithms=2, math=2")
    print()

    recommendations = recommend_courses(user_id=student.id, top_n=3)

    print("  Рекомендации (косинусное сходство с профилем):")
    print(f"  {'Курс':<25} {'Теги':<35} {'Сходство':>10}")
    print(f"  {'-'*25} {'-'*35} {'-'*10}")
    for rec in recommendations:
        tags_str = ", ".join(rec["tags"])
        print(f"  {rec['title']:<25} {tags_str:<35} {rec['similarity']:>10.4f}")

    print()
    print("  Формула: similarity = (A . B) / (|A| * |B|)")
    print("  Пример для 'Python Advanced' (python, programming, oop):")
    print("    A (Alice) = {python:2, programming:4, beginner:2, algorithms:2, math:2}")
    print("    B (курс)  = {python:1, programming:1, oop:1}")
    print("    A . B     = 2*1 + 4*1 + 0 = 6")
    print("    |A|       = sqrt(4+16+4+4+4) = sqrt(32) = 5.657")
    print("    |B|       = sqrt(1+1+1)      = sqrt(3)  = 1.732")
    print("    similarity= 6 / (5.657 * 1.732) = 0.6124")

    # -- Итог из БД ----------------------------------------------------
    separator("ИТОГ — Данные в БД")
    users = db.fetchall("SELECT * FROM users")
    print(f"  Users ({len(users)}):")
    for u in users:
        print(f"    [{u['id']}] {u['name']} — {u['role']}")

    courses = db.fetchall("SELECT * FROM courses")
    print(f"  Courses ({len(courses)}):")
    for c in courses:
        tags = db.fetchall("SELECT tag FROM course_tags WHERE course_id=?", (c['id'],))
        tags_str = ", ".join(t['tag'] for t in tags)
        print(f"    [{c['id']}] {c['title']:<25} ${c['price']:<8} tags: {tags_str}")

    enrollments = db.fetchall("SELECT * FROM enrollments")
    print(f"  Enrollments ({len(enrollments)}):")
    for e in enrollments:
        print(f"    user={e['user_id']} course={e['course_id']} completed={e['completed']}")

    print("\n  Все паттерны + рекомендательная система успешно продемонстрированы!\n")

if __name__ == "__main__":
    main()
