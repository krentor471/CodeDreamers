# services/student_observer.py — connects User (Observer) with CourseSubject
from models.user import User
from patterns.observer.course_observer import CourseObserver

class StudentObserver(CourseObserver):
    def __init__(self, user: User):
        self._user = user

    def update(self, course_title: str, event: str) -> None:
        message = f"[{course_title}] {event}"
        print(f"  [Notification] for {self._user.name}:")
        self._user.notify(message)
