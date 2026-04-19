# main.py — CodeDreamers: демонстрация всех паттернов
import os
import sys
import logging

# Фикс кодировки для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Удаляем старую БД для чистого запуска
if os.path.exists("codedreamers.db"):
    os.remove("codedreamers.db")

from config import ConfigManager
from database import DatabaseManager
from patterns.factory.user_factory import UserFactory
from patterns.factory.course_factory import CourseFactory
from patterns.decorator.course_decorator import WithCertificate, WithMentorSupport, WithLifetimeAccess
from patterns.command.course_commands import EnrollCommand, UnenrollCommand, CompleteCourseCommand, CommandHistory
from patterns.strategy.notification_strategy import EmailNotification, SMSNotification, TelegramNotification
from services.student_observer import StudentObserver

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

    # -- 2. Factory — создаём пользователей ---------------------------
    separator("2. FACTORY — Создание пользователей и курсов")
    student = UserFactory.create("Alice", "alice@example.com", "student")
    mentor  = UserFactory.create("Bob",   "bob@example.com",   "mentor")
    admin   = UserFactory.create("Carol", "carol@example.com", "admin")
    print(f"  {student}")
    print(f"  {mentor}")
    print(f"  {admin}")

    raw_course = CourseFactory.create(
        title="Python Basics",
        description="Learn Python from scratch",
        base_price=100.0,
        category="advanced"
    )
    print(f"\n  Raw course: {raw_course}")

    # -- 3. Decorator — оборачиваем курс ------------------------------
    separator("3. DECORATOR — Добавляем опции к курсу")
    decorated = WithCertificate(WithMentorSupport(raw_course))
    print(f"  Base price:      ${raw_course.get_price():.2f}")
    print(f"  + MentorSupport: ${WithMentorSupport(raw_course).get_price():.2f}")
    print(f"  + Certificate:   ${decorated.get_price():.2f}")
    print(f"  Description: {decorated.get_description()}")

    full_package = WithLifetimeAccess(decorated)
    print(f"  Full package:    ${full_package.get_price():.2f}")
    print(f"  Description: {full_package.get_description()}")

    # -- 4. Observer — подписка студента на курс ----------------------
    separator("4. OBSERVER — Подписка на обновления курса")
    alice_observer = StudentObserver(student)
    raw_course.subscribe(alice_observer)
    print(f"  {student.name} subscribed to '{raw_course.title}'")

    # -- 5. Strategy — меняем стратегию уведомлений ------------------
    separator("5. STRATEGY — Уведомления")
    print("  Default (Email):")
    student.notify("Welcome to CodeDreamers!")

    student.set_notification_strategy(SMSNotification())
    print("  Switched to SMS:")
    student.notify("Your course is ready!")

    student.set_notification_strategy(TelegramNotification())
    print("  Switched to Telegram:")
    student.notify("New lesson available!")

    # Возвращаем Email для Observer-уведомлений
    student.set_notification_strategy(EmailNotification())

    # -- 6. Command — запись на курс ----------------------------------
    separator("6. COMMAND — Операции с курсом")
    history = CommandHistory()

    result = history.execute(EnrollCommand(student, raw_course))
    print(f"  [OK] {result}")

    result = history.execute(CompleteCourseCommand(student, raw_course))
    print(f"  [OK] {result}")

    result = history.undo_last()
    print(f"  [UNDO] {result}")

    result = history.undo_last()
    print(f"  [UNDO] {result}")

    # -- 7. Observer + Strategy — новый урок -> уведомление ----------
    separator("7. OBSERVER + STRATEGY — Новый урок -> уведомление")
    raw_course.subscribe(alice_observer)
    raw_course.add_lesson("Variables and Data Types")

    # -- Итог из БД ---------------------------------------------------
    separator("ИТОГ — Данные в БД")
    users = db.fetchall("SELECT * FROM users")
    print(f"  Users ({len(users)}):")
    for u in users:
        print(f"    [{u['id']}] {u['name']} — {u['role']}")

    courses = db.fetchall("SELECT * FROM courses")
    print(f"  Courses ({len(courses)}):")
    for c in courses:
        print(f"    [{c['id']}] {c['title']} — ${c['price']}")

    enrollments = db.fetchall("SELECT * FROM enrollments")
    print(f"  Enrollments ({len(enrollments)}): {[dict(e) for e in enrollments]}")

    print("\n  Все паттерны успешно продемонстрированы!\n")

if __name__ == "__main__":
    main()
