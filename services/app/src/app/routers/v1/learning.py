"""Public catalog and student course progression, assessments, and account views."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import DB, CurrentUser, Limit, Offset, ResourceId, get_or_404, page
from app.models import Course
from app.schemas import (
    CourseView,
    Page,
    Search,
    UserView,
)

router = APIRouter(tags=["learning"])


@router.get("/courses", response_model=Page[CourseView])
async def catalog(
    db: DB,
    limit: Limit = 20,
    offset: Offset = 0,
    search: Search | None = None,
):
    statement = select(Course).where(Course.published.is_(True)).order_by(Course.id)
    if search:
        statement = statement.where(Course.title.icontains(search, autoescape=True))
    return await page(db, statement, limit, offset)


@router.get("/courses/{course_id}", response_model=CourseView)
async def course_detail(course_id: ResourceId, db: DB):
    course = await get_or_404(db, Course, course_id)
    if not course.published:
        raise HTTPException(404, "Course not found")
    return course


@router.get("/me", response_model=UserView, tags=["account"])
async def profile(user: CurrentUser):
    return user
