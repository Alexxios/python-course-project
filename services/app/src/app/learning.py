"""Enrollment, ordered access, completion, and grading rules."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_or_404
from app.models import Completion, Course, Enrollment, Lesson, Question
from app.schemas import CourseView, Progress, Submission


async def editable_course(db: AsyncSession, course_id: int) -> Course:
    course = await db.scalar(select(Course).where(Course.id == course_id).with_for_update())
    if course is None:
        raise HTTPException(404, "Course not found")
    if await db.scalar(select(Enrollment.id).where(Enrollment.course_id == course_id).limit(1)):
        raise HTTPException(
            409, "Course content is frozen after enrollment; create a new course revision"
        )
    return course


async def enrollment_for(db: AsyncSession, user_id: int, course_id: int) -> Enrollment:
    enrollment = await db.scalar(
        select(Enrollment)
        .where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .with_for_update()
    )
    if enrollment is None:
        raise HTTPException(403, "Enroll in this course first")
    return enrollment


async def course_lessons(db: AsyncSession, course_id: int) -> list[Lesson]:
    return list(
        await db.scalars(
            select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.position, Lesson.id)
        )
    )


async def completed_ids(db: AsyncSession, enrollment: Enrollment) -> set[int]:
    return set(
        await db.scalars(
            select(Completion.lesson_id).where(Completion.enrollment_id == enrollment.id)
        )
    )


async def accessible_lesson(
    db: AsyncSession, user_id: int, lesson_id: int
) -> tuple[Lesson, Enrollment]:
    lesson = await get_or_404(db, Lesson, lesson_id)
    enrollment = await enrollment_for(db, user_id, lesson.course_id)
    completed = await completed_ids(db, enrollment)
    earlier = await db.scalars(
        select(Lesson.id).where(
            Lesson.course_id == lesson.course_id, Lesson.position < lesson.position
        )
    )
    if any(identity not in completed for identity in earlier):
        raise HTTPException(403, "Complete preceding lessons first")
    return lesson, enrollment


async def questions_for(db: AsyncSession, lesson_id: int) -> list[Question]:
    return list(
        await db.scalars(
            select(Question)
            .where(Question.lesson_id == lesson_id)
            .order_by(Question.position, Question.id)
        )
    )


async def mark_completed(db: AsyncSession, enrollment: Enrollment, lesson_id: int) -> None:
    if lesson_id not in (await completed_ids(db, enrollment)):
        db.add(Completion(enrollment_id=enrollment.id, lesson_id=lesson_id))
        await db.flush()


async def progress_for(db: AsyncSession, enrollment: Enrollment) -> Progress:
    lessons = await course_lessons(db, enrollment.course_id)
    completed = await completed_ids(db, enrollment)
    done = sum(lesson.id in completed for lesson in lessons)
    return Progress(
        course=CourseView.model_validate(await db.get(Course, enrollment.course_id)),
        total_lessons=len(lessons),
        completed_lessons=done,
        progress_percent=round(100 * done / len(lessons), 2) if lessons else 0,
        next_lesson_id=next((lesson.id for lesson in lessons if lesson.id not in completed), None),
    )


def grade_answers(questions: list[dict], submission: Submission) -> tuple[int, float]:
    expected = {question["id"]: question for question in questions}
    if not expected or {answer.question_id for answer in submission.answers} != set(expected):
        raise HTTPException(422, "Submit exactly one answer for each question in this test")
    correct = 0
    for answer in submission.answers:
        question = expected[answer.question_id]
        if answer.option >= len(question["options"]):
            raise HTTPException(422, "Selected option does not exist")
        correct += answer.option == question["correct_option"]
    return correct, round(100 * correct / len(expected), 2)
