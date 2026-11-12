"""INSERT and SELECT operations; each write is one complete transaction."""

import csv
from pathlib import Path

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import sessionmaker

from app.students.models import StudentGrade
from app.students.schemas import Grade, GradeCreate, Student

CSV_COLUMNS = {
    "Фамилия": "last_name",
    "Имя": "first_name",
    "Факультет": "faculty",
    "Курс": "course",
    "Оценка": "grade",
}


class StudentRepository:
    def __init__(self, engine: Engine) -> None:
        self.sessions = sessionmaker(engine)

    def insert(self, grade: GradeCreate) -> Grade:
        with self.sessions.begin() as session:
            record = StudentGrade(**grade.model_dump())
            session.add(record)
            session.flush()
            return Grade.model_validate(record)

    def select_all(self) -> list[Grade]:
        with self.sessions() as session:
            records = session.scalars(select(StudentGrade).order_by(StudentGrade.id))
            return [Grade.model_validate(record) for record in records]

    def import_csv(self, path: str | Path) -> int:
        """Append every row, or roll back the entire import on any failure."""
        count = 0
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            try:
                if reader.fieldnames is None or (
                    len(reader.fieldnames) != len(CSV_COLUMNS)
                    or set(reader.fieldnames) != set(CSV_COLUMNS)
                ):
                    raise ValueError("CSV headers must be: " + ", ".join(CSV_COLUMNS))
                with self.sessions.begin() as session:
                    for row in reader:
                        if None in row or any(value is None for value in row.values()):
                            raise ValueError(f"CSV line {reader.line_num}: expected five fields")
                        values = {field: row[column] for column, field in CSV_COLUMNS.items()}
                        try:
                            values["grade"] = int(values["grade"])
                            grade = GradeCreate.model_validate(values)
                        except ValueError as exc:
                            raise ValueError(
                                f"CSV line {reader.line_num}: invalid student or grade (0..100)"
                            ) from exc
                        session.add(StudentGrade(**grade.model_dump()))
                        # Flush inside the transaction so even a late failure rolls back prior rows.
                        session.flush()
                        count += 1
            except csv.Error as exc:
                # DictReader only updates its line_num after a successful read.
                raise ValueError(f"CSV line {reader.reader.line_num}: malformed CSV") from exc
        return count

    def students_by_faculty(self, faculty: str) -> list[Student]:
        return self._students(StudentGrade.faculty == faculty)

    def unique_courses(self) -> list[str]:
        with self.sessions() as session:
            return list(
                session.scalars(
                    select(StudentGrade.course).distinct().order_by(StudentGrade.course)
                )
            )

    def students_below_30(self, course: str) -> list[Student]:
        return self._students(StudentGrade.course == course, StudentGrade.grade < 30)

    def average_grade_by_faculty(self, faculty: str) -> float | None:
        with self.sessions() as session:
            return session.scalar(
                select(func.avg(StudentGrade.grade)).where(StudentGrade.faculty == faculty)
            )

    def _students(self, *conditions) -> list[Student]:
        columns = (StudentGrade.last_name, StudentGrade.first_name, StudentGrade.faculty)
        with self.sessions() as session:
            rows = session.execute(
                select(*columns).where(*conditions).distinct().order_by(*columns)
            )
            return [Student.model_validate(dict(row)) for row in rows.mappings()]
