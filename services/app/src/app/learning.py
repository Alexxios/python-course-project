"""Enrollment, ordered access, completion, and grading rules."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Course, Enrollment


async def editable_course(db: AsyncSession, course_id: int) -> Course:
    course = await db.scalar(select(Course).where(Course.id == course_id).with_for_update())
    if course is None:
        raise HTTPException(404, "Course not found")
    if await db.scalar(select(Enrollment.id).where(Enrollment.course_id == course_id).limit(1)):
        raise HTTPException(
            409, "Course content is frozen after enrollment; create a new course revision"
        )
    return course
