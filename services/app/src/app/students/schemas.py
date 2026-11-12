"""Shared input validation and result shapes for the repository, CLI, and API."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def validate_text(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Use valid Unicode text") from exc
    if "\x00" in value:
        raise ValueError("NUL characters are not allowed")
    return value


StudentText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    AfterValidator(validate_text),
]


class Student(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    last_name: StudentText
    first_name: StudentText
    faculty: StudentText


class GradeCreate(Student):
    course: StudentText
    grade: Annotated[int, Field(strict=True, ge=0, le=100)]


class Grade(GradeCreate):
    id: int


class FacultyAverage(BaseModel):
    faculty: StudentText
    average_grade: float | None
