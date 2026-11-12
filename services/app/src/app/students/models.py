"""Preserve each source row, including repeated grades, in its own record."""

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StudentGrade(Base):
    __tablename__ = "student_grades"
    __table_args__ = (
        CheckConstraint("grade >= 0 AND grade <= 100", name="ck_student_grades_grade"),
        *(
            CheckConstraint(
                f"length(trim({column})) > 0 AND length({column}) <= 200",
                name=f"ck_student_grades_{column}",
            )
            for column in ("last_name", "first_name", "faculty", "course")
        ),
        Index("ix_student_grades_faculty", "faculty"),
        Index("ix_student_grades_course_grade", "course", "grade"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    last_name: Mapped[str] = mapped_column(String(200))
    first_name: Mapped[str] = mapped_column(String(200))
    faculty: Mapped[str] = mapped_column(String(200))
    course: Mapped[str] = mapped_column(String(200))
    grade: Mapped[int]
