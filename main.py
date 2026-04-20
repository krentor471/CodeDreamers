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
    separator("3. FACTORY — Специализированные объекты")

    # UserFactory возвращает Student / Mentor / Admin
    student = UserFactory.create("Demo Student", "demo@example.com",  "student")
    mentor  = UserFactory.create("Demo Mentor",  "mentor@example.com", "mentor")
    admin   = UserFactory.create("Demo Admin",   "admin@example.com",  "admin")

    print(f"  {student.__class__.__name__}: {student}")
    print(f"    permissions : {student.get_permissions()}")
    print(f"    discount    : {student.get_discount()*100:.0f}%")
    print(f"    strategy    : {student._strategy.channel_name}")
    print()
    print(f"  {mentor.__class__.__name__}: {mentor}")
    print(f"    permissions : {mentor.get_permissions()}")
    print(f"    hourly_rate : ${mentor.get_hourly_rate():.2f}")
    print(f"    strategy    : {mentor._strategy.channel_name}")
    print()
    print(f"  {admin.__class__.__name__}: {admin}")
    print(f"    permissions : {admin.get_permissions()}")
    print(f"    can_delete  : {admin.can_delete()}")
    print(f"    strategy    : {admin._strategy.channel_name}")

    # CourseFactory возвращает BasicCourse / AdvancedCourse / ProfessionalCourse
    print()
    c1_row = db.fetchone("SELECT * FROM courses WHERE title='Python Basics'")
    c4_row = db.fetchone("SELECT * FROM courses WHERE title='Algorithms'")
    from models.course import BasicCourse, ProfessionalCourse
    c1 = BasicCourse(id=c1_row["id"], title=c1_row["title"],
                     description=c1_row["description"], price=c1_row["price"])
    c4 = ProfessionalCourse(id=c4_row["id"], title=c4_row["title"],
                            description=c4_row["description"], price=c4_row["price"])
    print(f"  {c1.__class__.__name__}: '{c1.title}'")
    print(f"    max_students: {c1.get_max_students()} | support: {c1.get_support_level()}")
    print(f"  {c4.__class__.__name__}: '{c4.title}'")
    print(f"    max_students: {c4.get_max_students()} | support: {c4.get_support_level()}")

    # -- 4. Decorator --------------------------------------------------
    separator("4. DECORATOR — CourseBuilder + сохранение пакетов в БД")
    from patterns.decorator.course_decorator import CourseBuilder

    # Пакет 1: только сертификат
    pkg1 = CourseBuilder(c1).add("certificate").build()
    print(f"  Package 1: {pkg1.get_description()}")
    print(f"             Price: ${pkg1.get_price():.2f}")

    # Пакет 2: сертификат + ментор
    pkg2 = CourseBuilder(c1).add("certificate").add("mentor_support").build()
    print(f"  Package 2: {pkg2.get_description()}")
    print(f"             Price: ${pkg2.get_price():.2f}")

    # Пакет 3: все опции
    pkg3 = CourseBuilder(c4).add("certificate").add("mentor_support").add("lifetime_access").build()
    print(f"  Package 3: {pkg3.get_description()}")
    print(f"             Price: ${pkg3.get_price():.2f}")

    # Показываем сохранённые пакеты из БД
    packages = db.fetchall("SELECT * FROM course_packages")
    print(f"\n  Packages saved in DB ({len(packages)}):")
    for p in packages:
        print(f"    [{p['id']}] course_id={p['course_id']} | "
              f"options: {p['options']} | ${p['final_price']:.2f}")

    # -- 5. Observer ---------------------------------------------------
    separator("5. OBSERVER — Подписка на обновления курса")
    alice_observer = StudentObserver(student)
    c1.subscribe(alice_observer)
    print(f"  {student.name} subscribed to '{c1.title}'")

    # -- 6. Strategy ---------------------------------------------------
    separator("6. STRATEGY — Уведомления")
    print(f"  Стратегия по умолчанию для student: {student._strategy.channel_name}")
    print("  Отправка через Email (default для student):")
    student.notify("Welcome to CodeDreamers!")

    print("  Смена стратегии на SMS:")
    student.set_notification_strategy(SMSNotification())
    student.notify("Your course is ready!")

    print("  Смена стратегии на Telegram:")
    student.set_notification_strategy(TelegramNotification())
    student.notify("New lesson available!")

    # Возвращаем Email (default для student)
    student.set_notification_strategy(EmailNotification())

    # История уведомлений из БД
    notifs = db.fetchall("SELECT * FROM notifications ORDER BY id DESC LIMIT 3")
    print(f"\n  Последние уведомления в БД ({len(notifs)}):")
    print(f"  {'#':<4} {'channel':<10} {'recipient':<25} {'message'}")
    print(f"  {'-'*4} {'-'*10} {'-'*25} {'-'*30}")
    for n in reversed(notifs):
        print(f"  [{n['id']}] {n['channel']:<10} {n['recipient']:<25} {n['message'][:40]}")

    # -- 7. Command + State Machine -----------------------------------
    separator("7. COMMAND + STATE MACHINE — Enrollment")
    from patterns.state.enrollment_state import EnrollmentContext
    history = CommandHistory()

    print("  Переходы состояний Enrollment:")
    print()

    # (нет) -> ACTIVE
    r = history.execute(EnrollCommand(student, c1))
    print(f"  [*]       -> ACTIVE    : {r}")

    # ACTIVE -> COMPLETED
    r = history.execute(CompleteCourseCommand(student, c1))
    print(f"  ACTIVE    -> COMPLETED : {r}")

    # COMPLETED -> ACTIVE (reopen через undo)
    r = history.undo_last()
    print(f"  COMPLETED -> ACTIVE    : {r}")

    # ACTIVE -> CANCELLED (cancel через undo enroll)
    r = history.undo_last()
    print(f"  ACTIVE    -> CANCELLED : {r}")

    # CANCELLED -> ACTIVE (re-enroll)
    r = history.execute(EnrollCommand(student, c1))
    print(f"  CANCELLED -> ACTIVE    : {r}")

    # ACTIVE -> COMPLETED (финально для рекомендаций)
    history.execute(CompleteCourseCommand(student, c1))
    history.execute(EnrollCommand(student, c4))
    history.execute(CompleteCourseCommand(student, c4))

    # Показываем статусы из БД
    print()
    rows = DatabaseManager().fetchall("""
        SELECT e.status, u.name as uname, c.title as ctitle
        FROM enrollments e
        JOIN users u ON e.user_id=u.id
        JOIN courses c ON e.course_id=c.id
        WHERE e.user_id = ?
    """, (student.id,))
    print(f"  Enrollments for {student.name} (из БД):")
    for row in rows:
        print(f"    {row['ctitle']:<25} status: {row['status'].upper()}")

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
        print(f"    [{e['id']}] {e['uname']:<15} -> {e['ctitle']:<25} [{e['status'].upper()}]")

    total = (db.fetchone("SELECT COUNT(*) as n FROM users")["n"] +
             db.fetchone("SELECT COUNT(*) as n FROM courses")["n"] +
             db.fetchone("SELECT COUNT(*) as n FROM lessons")["n"] +
             db.fetchone("SELECT COUNT(*) as n FROM enrollments")["n"] +
             db.fetchone("SELECT COUNT(*) as n FROM course_tags")["n"])
    print(f"\n  TOTAL records in DB: {total}")

    notifications = db.fetchall("SELECT * FROM notifications ORDER BY id")
    print(f"\n  Notifications ({len(notifications)}):")
    print(f"  {'#':<4} {'channel':<10} {'recipient':<25} {'message'}")
    print(f"  {'-'*4} {'-'*10} {'-'*25} {'-'*35}")
    for n in notifications:
        print(f"  [{n['id']}] {n['channel']:<10} {n['recipient']:<25} {n['message'][:40]}")

    print("\n  Все паттерны + рекомендательная система успешно продемонстрированы!\n")

if __name__ == "__main__":
    main()
