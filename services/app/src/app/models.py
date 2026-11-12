"""Relational learning platform model; timestamps are UTC Unix seconds."""

import time

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> int:
    return int(time.time())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student', 'admin')", name="ck_user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student")
    created_at: Mapped[int] = mapped_column(default=now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    access_hash: Mapped[str] = mapped_column(String(64), unique=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    access_expires_at: Mapped[int]
    refresh_expires_at: Mapped[int]


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (CheckConstraint("passing_score BETWEEN 1 AND 100", name="ck_course_score"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(default=False, index=True)
    passing_score: Mapped[int] = mapped_column(default=70)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[int] = mapped_column(default=now)


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("course_id", "position", name="uq_lesson_position"),
        CheckConstraint("position > 0", name="ck_lesson_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    position: Mapped[int]
    video_url: Mapped[str | None] = mapped_column(String(2048))


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("lesson_id", "position", name="uq_question_position"),
        CheckConstraint("position > 0", name="ck_question_position"),
        CheckConstraint("correct_option >= 0 AND correct_option < 6", name="ck_question_option"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON)
    correct_option: Mapped[int]
    position: Mapped[int]


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="RESTRICT"), index=True
    )
    enrolled_at: Mapped[int] = mapped_column(default=now)


class Completion(Base):
    __tablename__ = "completions"
    __table_args__ = (UniqueConstraint("enrollment_id", "lesson_id", name="uq_completion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
    completed_at: Mapped[int] = mapped_column(default=now)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="RESTRICT"), index=True
    )
    answers: Mapped[list[dict]] = mapped_column(JSON)
    correct_count: Mapped[int]
    question_count: Mapped[int]
    score: Mapped[float]
    passed: Mapped[bool]
    created_at: Mapped[int] = mapped_column(default=now)


class PracticeQuiz(Base):
    __tablename__ = "practice_quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(20))
    questions: Mapped[list[dict]] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(default=now)
    submitted_at: Mapped[int | None]
    score: Mapped[float | None]
    answers: Mapped[list[dict] | None] = mapped_column(JSON)
