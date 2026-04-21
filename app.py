# app.py — Flask-сервер CodeDreamers
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Инициализируем БД и seed до старта Flask
if not os.path.exists("codedreamers.db"):
    from config import ConfigManager
    from database import DatabaseManager
    ConfigManager()
    DatabaseManager()
    from seed import seed
    seed()

from flask import Flask, jsonify, request, send_from_directory
from patterns.proxy.course_service_proxy import CourseServiceProxy

app = Flask(__name__, static_folder="static", static_url_path="")


def get_proxy() -> CourseServiceProxy:
    """Создаёт Proxy с ролью из заголовка X-Role (по умолчанию student)."""
    role = request.headers.get("X-Role", "student").lower()
    return CourseServiceProxy(role)


# ── Фронтенд ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── API: курсы ────────────────────────────────────────────────────────────

@app.route("/api/courses")
def api_courses():
    try:
        return jsonify(get_proxy().get_courses())
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


@app.route("/api/courses/<int:course_id>")
def api_course(course_id):
    try:
        course = get_proxy().get_course(course_id)
        if not course:
            return jsonify({"error": "Not found"}), 404
        return jsonify(course)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ── API: уроки ────────────────────────────────────────────────────────────

@app.route("/api/courses/<int:course_id>/lessons")
def api_lessons(course_id):
    try:
        return jsonify(get_proxy().get_lessons(course_id))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ── API: программа (Composite) ────────────────────────────────────────────

@app.route("/api/courses/<int:course_id>/program")
def api_program(course_id):
    try:
        return jsonify(get_proxy().get_program(course_id))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ── API: записи студента ──────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>/enrollments")
def api_enrollments(user_id):
    try:
        return jsonify(get_proxy().get_enrollments(user_id))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


# ── API: пользователи (mentor/admin) ─────────────────────────────────────

@app.route("/api/users")
def api_users():
    try:
        return jsonify(get_proxy().get_users())
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403


if __name__ == "__main__":
    app.run(debug=True, port=5000)
