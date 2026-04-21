# main.py — CodeDreamers: все операции через интерфейс Command
import os
import sys
import logging

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

if os.path.exists("codedreamers.db"):
    os.remove("codedreamers.db")

from config import ConfigManager
from database import DatabaseManager
from patterns.command.course_commands import (
    EnrollCommand, UnenrollCommand, CompleteCourseCommand, CommandHistory
)
from patterns.command.system_commands import (
    CreateUserCommand, ChangeStrategyCommand,
    CreateCourseCommand, AddLessonCommand, ApplyDecoratorCommand,
    RevenueReportCommand, TopStudentsCommand,
    RecommendCommand, SubscribeCommand,
    GenerateContentCommand,
)
from patterns.strategy.notification_strategy import SMSNotification, TelegramNotification
from patterns.adapter.analytics_adapter import AnalyticsAdapter
from patterns.observer.event_bus import EventBus
from services.system_observers import (
    LogObserver, AuditObserver, AnalyticsObserver, NotificationObserver
)
from models.course import BasicCourse, ProfessionalCourse
from seed import seed

logger = logging.getLogger(__name__)


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def main():
    # ── Singleton ─────────────────────────────────────────────────────
    separator("1. SINGLETON — Config & Database")
    cfg = ConfigManager()
    db  = DatabaseManager()
    print(f"  ConfigManager singleton: {cfg is ConfigManager()}")
    print(f"  DatabaseManager singleton: {db is DatabaseManager()}")

    # ── EventBus ──────────────────────────────────────────────────────
    separator("EVENT BUS — Системные наблюдатели")
    bus = EventBus()
    LogObserver()
    AuditObserver()
    AnalyticsObserver()
    NotificationObserver()
    print(f"  EventBus singleton: {bus is EventBus()}")
    print("  Подписчики: Log, Audit, Analytics, Notification")

    # ── Seed ──────────────────────────────────────────────────────────
    separator("2. SEED — Заполнение БД")
    counts = seed()
    print(f"  users={counts['users']} courses={counts['courses']} "
          f"lessons={counts['lessons']} enrollments={counts['enrollments']} "
          f"tags={counts['tags']}  TOTAL={sum(counts.values())}")

    # ── Единый CommandHistory для всей системы ────────────────────────
    history = CommandHistory()

    # ── 3. CreateUserCommand ──────────────────────────────────────────
    separator("3. COMMAND: CreateUserCommand")
    cmd_student = CreateUserCommand("Demo Student", "demo@example.com",  "student")
    cmd_mentor  = CreateUserCommand("Demo Mentor",  "mentor@example.com", "mentor")
    cmd_admin   = CreateUserCommand("Demo Admin",   "admin@example.com",  "admin")

    print(f"  >> {history.execute(cmd_student)}")
    print(f"  >> {history.execute(cmd_mentor)}")
    print(f"  >> {history.execute(cmd_admin)}")

    student = cmd_student.result
    mentor  = cmd_mentor.result
    admin   = cmd_admin.result

    print(f"\n  Student permissions : {student.get_permissions()}")
    print(f"  Mentor  permissions : {mentor.get_permissions()}")
    print(f"  Admin   permissions : {admin.get_permissions()}")

    # Undo создания admin — демонстрация отмены
    print(f"\n  {history.undo_last()}")

    # ── 4. CreateCourseCommand ────────────────────────────────────────
    separator("4. COMMAND: CreateCourseCommand")
    c1_row = db.fetchone("SELECT * FROM courses WHERE title='Python Basics'")
    c4_row = db.fetchone("SELECT * FROM courses WHERE title='Algorithms'")
    c1 = BasicCourse(id=c1_row["id"], title=c1_row["title"],
                     description=c1_row["description"], price=c1_row["price"])
    c4 = ProfessionalCourse(id=c4_row["id"], title=c4_row["title"],
                            description=c4_row["description"], price=c4_row["price"])

    cmd_course = CreateCourseCommand(
        "Machine Learning", "ML from scratch", 120.0, "professional",
        tags=["python", "math", "ml", "data"]
    )
    print(f"  >> {history.execute(cmd_course)}")
    new_course = cmd_course.result

    # Undo создания курса
    print(f"  {history.undo_last()}")

    # ── 5. ApplyDecoratorCommand ──────────────────────────────────────
    separator("5. COMMAND: ApplyDecoratorCommand")
    cmd_pkg1 = ApplyDecoratorCommand(c1, ["certificate"])
    cmd_pkg2 = ApplyDecoratorCommand(c1, ["certificate", "mentor_support"])
    cmd_pkg3 = ApplyDecoratorCommand(c4, ["certificate", "mentor_support", "lifetime_access"])

    print(f"  >> {history.execute(cmd_pkg1)}")
    print(f"  >> {history.execute(cmd_pkg2)}")
    print(f"  >> {history.execute(cmd_pkg3)}")

    packages = db.fetchall("SELECT * FROM course_packages")
    print(f"\n  Packages in DB ({len(packages)}):")
    for p in packages:
        print(f"    [{p['id']}] {p['options']:<40} ${p['final_price']:.2f}")

    # ── 6. SubscribeCommand ───────────────────────────────────────────
    separator("6. COMMAND: SubscribeCommand")
    cmd_sub = SubscribeCommand(student, c1)
    print(f"  >> {history.execute(cmd_sub)}")

    # ── 7. ChangeStrategyCommand ──────────────────────────────────────
    separator("7. COMMAND: ChangeStrategyCommand")
    print(f"  Current strategy: {student._strategy.channel_name}")
    cmd_sms = ChangeStrategyCommand(student, SMSNotification())
    print(f"  >> {history.execute(cmd_sms)}")
    student.notify("Your account is ready!")

    cmd_tg = ChangeStrategyCommand(student, TelegramNotification())
    print(f"  >> {history.execute(cmd_tg)}")
    student.notify("New course available!")

    # Undo — возвращаем SMS
    print(f"  {history.undo_last()}")
    # Undo — возвращаем Email
    print(f"  {history.undo_last()}")
    print(f"  Restored strategy: {student._strategy.channel_name}")

    # ── 8. EnrollCommand / CompleteCourseCommand ──────────────────────
    separator("8. COMMAND: Enroll + Complete + State Machine")
    print(f"  >> {history.execute(EnrollCommand(student, c1))}")
    print(f"  >> {history.execute(CompleteCourseCommand(student, c1))}")
    print(f"  >> {history.execute(EnrollCommand(student, c4))}")
    print(f"  >> {history.execute(CompleteCourseCommand(student, c4))}")

    rows = db.fetchall("""
        SELECT e.status, c.title as ctitle FROM enrollments e
        JOIN courses c ON e.course_id=c.id WHERE e.user_id=?
    """, (student.id,))
    print(f"\n  Enrollments for {student.name}:")
    for r in rows:
        print(f"    {r['ctitle']:<25} [{r['status'].upper()}]")

    # ── 9. AddLessonCommand ───────────────────────────────────────────
    separator("9. COMMAND: AddLessonCommand")
    cmd_lesson = AddLessonCommand(c1, "List Comprehensions", "Advanced list syntax", 4)
    print(f"  >> {history.execute(cmd_lesson)}")
    print(f"  {history.undo_last()}")
    print(f"  >> {history.execute(cmd_lesson)}")  # повторно

    # ── 10. RecommendCommand ──────────────────────────────────────────
    separator("10. COMMAND: RecommendCommand")
    cmd_rec = RecommendCommand(student, top_n=3)
    print(f"  >> {history.execute(cmd_rec)}")
    print(f"\n  Recommendations for '{student.name}':")
    print(f"  {'Course':<25} {'Tags':<30} {'Similarity':>10}")
    print(f"  {'-'*25} {'-'*30} {'-'*10}")
    for rec in cmd_rec.result:
        print(f"  {rec['title']:<25} {', '.join(rec['tags']):<30} {rec['similarity']:>10.4f}")

    # ── 11. RevenueReportCommand ──────────────────────────────────────
    separator("11. COMMAND: RevenueReportCommand")
    cmd_rev = RevenueReportCommand()
    print(f"  >> {history.execute(cmd_rev)}")
    report = cmd_rev.result
    print(f"\n  {'Course':<25} {'Enrolled':>8} {'Revenue':>10}")
    print(f"  {'-'*25} {'-'*8} {'-'*10}")
    for item in report["by_course"]:
        print(f"  {item['name']:<25} {item['enrolled']:>8} ${item['revenue']:>9.2f}")
    print(f"  {'TOTAL':<25} {'':>8} ${report['total']:>9.2f}")

    # ── 12. GenerateContentCommand (Template Method) ──────────────────
    separator("12. TEMPLATE METHOD: GenerateContentCommand")
    for fmt in ("text", "video", "quiz"):
        cmd_gen = GenerateContentCommand("Python Decorators", fmt)
        print(f"  >> {history.execute(cmd_gen)}")
        for line in cmd_gen.result.splitlines():
            print(f"     {line}")
        print()

    # ── 13. TopStudentsCommand ────────────────────────────────────────
    separator("13. COMMAND: TopStudentsCommand")
    cmd_top = TopStudentsCommand(top_n=3)
    print(f"  >> {history.execute(cmd_top)}")
    print(f"\n  Top students:")
    for i, s in enumerate(cmd_top.result, 1):
        print(f"    {i}. {s['uname']:<15} completed: {s['ucompleted']}")

    # ── Итог: история команд ──────────────────────────────────────────
    separator("ИТОГ — История команд")
    print(f"  Всего команд в истории: {len(history._history)}")
    print()
    for i, cmd in enumerate(history._history, 1):
        print(f"  [{i:>2}] {cmd.__class__.__name__}")

    # ── EventBus лог ──────────────────────────────────────────────────
    separator("EVENT BUS — Лог событий")
    from collections import Counter
    event_log = EventBus().get_log()
    counts_ev = Counter(e.event_type for e in event_log)
    print(f"  Всего событий: {len(event_log)}")
    print()
    print(f"  {'Event Type':<25} {'Count':>6}")
    print(f"  {'-'*25} {'-'*6}")
    for etype, cnt in sorted(counts_ev.items()):
        print(f"  {etype:<25} {cnt:>6}")

    audit = db.fetchall("SELECT event_type, COUNT(*) as n FROM audit_log GROUP BY event_type")
    print(f"\n  Audit log summary:")
    for a in audit:
        print(f"    {a['event_type']:<25} {a['n']} records")

    counters = db.fetchall("SELECT * FROM analytics_counters ORDER BY key")
    print(f"\n  Analytics counters:")
    for c in counters:
        print(f"    {c['key']:<35} = {c['value']}")

    print("\n  Все операции выполнены через интерфейс Command!\n")


if __name__ == "__main__":
    main()
