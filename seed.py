# seed.py — заполнение БД тестовыми данными (20+ записей)
import logging
from patterns.factory.user_factory import UserFactory
from patterns.factory.course_factory import CourseFactory
from patterns.command.course_commands import EnrollCommand, CompleteCourseCommand, CommandHistory
from database import DatabaseManager

logger = logging.getLogger(__name__)


def seed():
    db = DatabaseManager()
    history = CommandHistory()

    # ── ПОЛЬЗОВАТЕЛИ (8 штук) ─────────────────────────────────────────
    users_data = [
        ("Alice",   "alice@example.com",   "student"),
        ("Bob",     "bob@example.com",     "mentor"),
        ("Carol",   "carol@example.com",   "admin"),
        ("David",   "david@example.com",   "student"),
        ("Eva",     "eva@example.com",     "student"),
        ("Frank",   "frank@example.com",   "mentor"),
        ("Grace",   "grace@example.com",   "student"),
        ("Henry",   "henry@example.com",   "student"),
    ]
    users = [UserFactory.create(name, email, role) for name, email, role in users_data]
    alice, bob, carol, david, eva, frank, grace, henry = users
    logger.info(f"Seeded {len(users)} users")

    # ── КУРСЫ (8 штук) ────────────────────────────────────────────────
    courses_data = [
        ("Python Basics",       "Intro to Python",              80.0,  "basic",
         ["python", "programming", "beginner"]),
        ("Python Advanced",     "OOP, decorators, async",       80.0,  "advanced",
         ["python", "programming", "oop"]),
        ("Web with Django",     "Build web apps with Django",   80.0,  "advanced",
         ["python", "web", "django"]),
        ("Algorithms",          "Sorting, graphs, DP",          80.0,  "professional",
         ["algorithms", "programming", "math"]),
        ("Data Science",        "Pandas, NumPy, ML basics",     80.0,  "professional",
         ["python", "math", "data", "ml"]),
        ("JavaScript Basics",   "Intro to JS and DOM",          80.0,  "basic",
         ["javascript", "web", "beginner"]),
        ("React Frontend",      "Components, hooks, state",     80.0,  "advanced",
         ["javascript", "web", "react"]),
        ("SQL & Databases",     "Relational DBs and queries",   80.0,  "basic",
         ["sql", "databases", "beginner"]),
    ]
    courses = [
        CourseFactory.create(title, desc, price, cat, tags=tags)
        for title, desc, price, cat, tags in courses_data
    ]
    c1, c2, c3, c4, c5, c6, c7, c8 = courses
    logger.info(f"Seeded {len(courses)} courses")

    # ── УРОКИ (20 штук, по 2-3 на курс) ──────────────────────────────
    lessons_data = [
        # Python Basics (c1)
        (c1.id, "Variables and Types",        "int, str, float, bool",          1),
        (c1.id, "Control Flow",               "if/else, for, while",            2),
        (c1.id, "Functions",                  "def, args, return",              3),
        # Python Advanced (c2)
        (c2.id, "Classes and OOP",            "class, inheritance, super()",    1),
        (c2.id, "Decorators",                 "@decorator pattern",             2),
        (c2.id, "Async/Await",                "asyncio basics",                 3),
        # Web with Django (c3)
        (c3.id, "Django Setup",               "startproject, settings",         1),
        (c3.id, "Models and ORM",             "models.py, migrations",          2),
        (c3.id, "Views and URLs",             "views.py, urls.py",              3),
        # Algorithms (c4)
        (c4.id, "Sorting Algorithms",         "bubble, merge, quick",           1),
        (c4.id, "Graph Traversal",            "BFS, DFS",                       2),
        (c4.id, "Dynamic Programming",        "memoization, tabulation",        3),
        # Data Science (c5)
        (c5.id, "NumPy Basics",               "arrays, operations",             1),
        (c5.id, "Pandas DataFrames",          "read_csv, groupby, merge",       2),
        # JavaScript Basics (c6)
        (c6.id, "Variables and Functions",    "var, let, const, arrow fn",      1),
        (c6.id, "DOM Manipulation",           "querySelector, events",          2),
        # React Frontend (c7)
        (c7.id, "Components and Props",       "functional components",          1),
        (c7.id, "useState and useEffect",     "hooks basics",                   2),
        # SQL & Databases (c8)
        (c8.id, "SELECT and WHERE",           "basic queries",                  1),
        (c8.id, "JOINs",                      "INNER, LEFT, RIGHT JOIN",        2),
    ]
    for course_id, title, content, order_num in lessons_data:
        db.execute(
            "INSERT INTO lessons (course_id, title, content, order_num) VALUES (?, ?, ?, ?)",
            (course_id, title, content, order_num)
        )
    logger.info(f"Seeded {len(lessons_data)} lessons")

    # ── ЗАПИСИ НА КУРСЫ (20 штук) ─────────────────────────────────────
    # (user, course, completed)
    enrollments_data = [
        (alice,  c1, True),   (alice,  c4, True),   (alice,  c2, False),
        (david,  c1, True),   (david,  c6, True),   (david,  c7, False),
        (eva,    c5, True),   (eva,    c4, False),   (eva,    c8, True),
        (grace,  c2, True),   (grace,  c3, True),   (grace,  c5, False),
        (henry,  c6, True),   (henry,  c7, True),   (henry,  c8, False),
        (alice,  c5, False),
        (david,  c4, False),
        (eva,    c2, False),
        (grace,  c1, True),
        (henry,  c3, False),
    ]
    for user, course, completed in enrollments_data:
        history.execute(EnrollCommand(user, course))
        if completed:
            history.execute(CompleteCourseCommand(user, course))
    logger.info(f"Seeded {len(enrollments_data)} enrollments")

    # ── Итоговая статистика ───────────────────────────────────────────
    counts = {
        "users":    db.fetchone("SELECT COUNT(*) as n FROM users")["n"],
        "courses":  db.fetchone("SELECT COUNT(*) as n FROM courses")["n"],
        "lessons":  db.fetchone("SELECT COUNT(*) as n FROM lessons")["n"],
        "enrollments": db.fetchone("SELECT COUNT(*) as n FROM enrollments")["n"],
        "tags":     db.fetchone("SELECT COUNT(*) as n FROM course_tags")["n"],
    }
    total = sum(counts.values())
    logger.info(f"Seed complete. Total records: {total}")
    return counts
