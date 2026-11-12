"""Public catalog and student course progression, assessments, and account views."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import DB, CurrentUser, FilterId, Limit, Offset, ResourceId, get_or_404, page
from app.learning import (
    accessible_lesson,
    completed_ids,
    course_lessons,
    enrollment_for,
    grade_answers,
    mark_completed,
    progress_for,
    questions_for,
)
from app.models import Attempt, Course, Enrollment
from app.schemas import (
    AttemptView,
    CourseView,
    LessonContent,
    LessonOutline,
    LessonView,
    Page,
    Progress,
    Search,
    StudentQuestion,
    Submission,
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


@router.post("/courses/{course_id}/enroll", response_model=Progress, status_code=201)
async def enroll(course_id: ResourceId, user: CurrentUser, db: DB):
    course = await db.scalar(select(Course).where(Course.id == course_id).with_for_update())
    if course is None or not course.published:
        raise HTTPException(404, "Course not found")
    enrollment = Enrollment(user_id=user.id, course_id=course_id)
    db.add(enrollment)
    await db.flush()
    return await progress_for(db, enrollment)


@router.get("/courses/{course_id}/lessons", response_model=list[LessonOutline])
async def curriculum(course_id: ResourceId, user: CurrentUser, db: DB):
    await get_or_404(db, Course, course_id)
    enrollment = await enrollment_for(db, user.id, course_id)
    completed = await completed_ids(db, enrollment)
    unlocked = True
    result = []
    for lesson in await course_lessons(db, course_id):
        result.append(
            LessonOutline(
                id=lesson.id,
                title=lesson.title,
                description=lesson.description,
                position=lesson.position,
                unlocked=unlocked,
                completed=lesson.id in completed,
            )
        )
        unlocked = unlocked and lesson.id in completed
    return result


@router.get("/lessons/{lesson_id}", response_model=LessonContent)
async def lesson_content(lesson_id: ResourceId, user: CurrentUser, db: DB):
    lesson, enrollment = await accessible_lesson(db, user.id, lesson_id)
    return LessonContent(
        **LessonView.model_validate(lesson).model_dump(),
        questions=[
            StudentQuestion.model_validate(question)
            for question in (await questions_for(db, lesson_id))
        ],
        completed=lesson_id in (await completed_ids(db, enrollment)),
    )


@router.post("/lessons/{lesson_id}/complete", response_model=Progress)
async def complete_lesson(lesson_id: ResourceId, user: CurrentUser, db: DB):
    lesson, enrollment = await accessible_lesson(db, user.id, lesson_id)
    if (await questions_for(db, lesson_id)) and lesson.id not in (
        await completed_ids(db, enrollment)
    ):
        raise HTTPException(409, "Pass this lesson's test before completing it")
    await mark_completed(db, enrollment, lesson_id)
    return await progress_for(db, enrollment)


@router.post("/lessons/{lesson_id}/attempts", response_model=AttemptView, status_code=201)
async def submit_test(lesson_id: ResourceId, payload: Submission, user: CurrentUser, db: DB):
    lesson, enrollment = await accessible_lesson(db, user.id, lesson_id)
    questions = await questions_for(db, lesson_id)
    if not questions:
        raise HTTPException(409, "This lesson has no test; mark it complete after reading")
    correct, score = grade_answers(
        [{"id": q.id, "options": q.options, "correct_option": q.correct_option} for q in questions],
        payload,
    )
    course = await db.get(Course, lesson.course_id)
    passed = correct * 100 >= course.passing_score * len(questions)
    attempt = Attempt(
        enrollment_id=enrollment.id,
        lesson_id=lesson_id,
        answers=payload.model_dump()["answers"],
        correct_count=correct,
        question_count=len(questions),
        score=score,
        passed=passed,
    )
    db.add(attempt)
    if passed:
        await mark_completed(db, enrollment, lesson_id)
    await db.flush()
    return attempt


@router.get("/me", response_model=UserView, tags=["account"])
async def profile(user: CurrentUser):
    return user


@router.get("/me/courses", response_model=Page[Progress], tags=["account"])
async def my_courses(user: CurrentUser, db: DB, limit: Limit = 20, offset: Offset = 0):
    result = await page(
        db,
        select(Enrollment).where(Enrollment.user_id == user.id).order_by(Enrollment.id),
        limit,
        offset,
    )
    result["items"] = [(await progress_for(db, enrollment)) for enrollment in result["items"]]
    return result


@router.get("/me/courses/{course_id}/progress", response_model=Progress, tags=["account"])
async def my_progress(course_id: ResourceId, user: CurrentUser, db: DB):
    return await progress_for(db, (await enrollment_for(db, user.id, course_id)))


@router.get("/me/attempts", response_model=Page[AttemptView], tags=["account"])
async def my_attempts(
    user: CurrentUser,
    db: DB,
    limit: Limit = 20,
    offset: Offset = 0,
    course_id: FilterId | None = None,
    lesson_id: FilterId | None = None,
):
    statement = (
        select(Attempt)
        .join(Enrollment)
        .where(Enrollment.user_id == user.id)
        .order_by(Attempt.id.desc())
    )
    if course_id is not None:
        statement = statement.where(Enrollment.course_id == course_id)
    if lesson_id is not None:
        statement = statement.where(Attempt.lesson_id == lesson_id)
    return await page(db, statement, limit, offset)
