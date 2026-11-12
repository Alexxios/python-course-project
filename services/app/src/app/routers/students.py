"""Assignment 6 database operations exposed through the existing FastAPI service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.students.repository import StudentRepository
from app.students.schemas import FacultyAverage, Grade, GradeCreate, Student, StudentText

router = APIRouter(
    prefix="/students",
    tags=["students"],
    responses={503: {"description": "The student database is unavailable"}},
)


def get_repository(request: Request) -> StudentRepository:
    return request.app.state.student_repository


Repository = Annotated[StudentRepository, Depends(get_repository)]


@router.post(
    "/grades",
    status_code=status.HTTP_201_CREATED,
    response_model=Grade,
    responses={400: {"description": "The request body could not be decoded"}},
)
def insert_grade(grade: GradeCreate, repository: Repository) -> Grade:
    return repository.insert(grade)


@router.get("/grades", response_model=list[Grade])
def select_grades(repository: Repository) -> list[Grade]:
    return repository.select_all()


@router.get("", response_model=list[Student])
def students_by_faculty(faculty: StudentText, repository: Repository) -> list[Student]:
    return repository.students_by_faculty(faculty)


@router.get("/courses", response_model=list[str])
def courses(repository: Repository) -> list[str]:
    return repository.unique_courses()


@router.get("/low-grades", response_model=list[Student])
def students_below_30(course: StudentText, repository: Repository) -> list[Student]:
    return repository.students_below_30(course)


@router.get("/average", response_model=FacultyAverage)
def average_grade(faculty: StudentText, repository: Repository) -> FacultyAverage:
    return FacultyAverage(
        faculty=faculty, average_grade=repository.average_grade_by_faculty(faculty)
    )
