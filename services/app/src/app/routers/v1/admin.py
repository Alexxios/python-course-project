"""Administrator CRUD for course, lesson, and test-question resources."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select

from app.dependencies import DB, Admin, Limit, Offset, ResourceId, get_or_404, page, require_admin
from app.learning import editable_course
from app.models import Course, Lesson, Question
from app.schemas import (
    CourseCreate,
    CourseUpdate,
    CourseView,
    LessonView,
    LessonWrite,
    Page,
    QuestionView,
    QuestionWrite,
)

router = APIRouter(prefix="/admin", tags=["administration"], dependencies=[Depends(require_admin)])


@router.post("/courses", response_model=CourseView, status_code=201)
async def create_course(payload: CourseCreate, db: DB, admin: Admin):
    course = Course(**payload.model_dump(), author_id=admin.id)
    db.add(course)
    await db.flush()
    return course


@router.get("/courses", response_model=Page[CourseView])
async def list_courses(
    db: DB, limit: Limit = 20, offset: Offset = 0, published: bool | None = None
):
    statement = select(Course).order_by(Course.id)
    if published is not None:
        statement = statement.where(Course.published == published)
    return await page(db, statement, limit, offset)


@router.get("/courses/{course_id}", response_model=CourseView)
async def read_course(course_id: ResourceId, db: DB):
    return await get_or_404(db, Course, course_id)


@router.put("/courses/{course_id}", response_model=CourseView)
async def update_course(course_id: ResourceId, payload: CourseUpdate, db: DB):
    course = await editable_course(db, course_id)
    if payload.published and not (
        await db.scalar(select(Lesson.id).where(Lesson.course_id == course.id).limit(1))
    ):
        raise HTTPException(409, "Add at least one lesson before publishing")
    for key, value in payload.model_dump().items():
        setattr(course, key, value)
    await db.flush()
    return course


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(course_id: ResourceId, db: DB):
    await db.delete(await editable_course(db, course_id))
    return Response(status_code=204)


@router.post("/courses/{course_id}/lessons", response_model=LessonView, status_code=201)
async def create_lesson(course_id: ResourceId, payload: LessonWrite, db: DB):
    await editable_course(db, course_id)
    lesson = Lesson(course_id=course_id, **payload.model_dump(mode="json"))
    db.add(lesson)
    await db.flush()
    return lesson


@router.get("/courses/{course_id}/lessons", response_model=Page[LessonView])
async def list_lessons(course_id: ResourceId, db: DB, limit: Limit = 20, offset: Offset = 0):
    await get_or_404(db, Course, course_id)
    return await page(
        db,
        select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.position, Lesson.id),
        limit,
        offset,
    )


@router.get("/lessons/{lesson_id}", response_model=LessonView)
async def read_lesson(lesson_id: ResourceId, db: DB):
    return await get_or_404(db, Lesson, lesson_id)


@router.put("/lessons/{lesson_id}", response_model=LessonView)
async def update_lesson(lesson_id: ResourceId, payload: LessonWrite, db: DB):
    lesson = await get_or_404(db, Lesson, lesson_id)
    await editable_course(db, lesson.course_id)
    for key, value in payload.model_dump(mode="json").items():
        setattr(lesson, key, value)
    await db.flush()
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=204)
async def delete_lesson(lesson_id: ResourceId, db: DB):
    lesson = await get_or_404(db, Lesson, lesson_id)
    course = await editable_course(db, lesson.course_id)
    if (
        course.published
        and (
            await db.scalar(
                select(func.count()).select_from(Lesson).where(Lesson.course_id == course.id)
            )
        )
        == 1
    ):
        raise HTTPException(409, "Unpublish the course before deleting its last lesson")
    await db.delete(lesson)
    return Response(status_code=204)


@router.post("/lessons/{lesson_id}/questions", response_model=QuestionView, status_code=201)
async def create_question(lesson_id: ResourceId, payload: QuestionWrite, db: DB):
    lesson = await get_or_404(db, Lesson, lesson_id)
    await editable_course(db, lesson.course_id)
    if (
        await db.scalar(
            select(func.count()).select_from(Question).where(Question.lesson_id == lesson_id)
        )
    ) >= 100:
        raise HTTPException(409, "A lesson test can contain at most 100 questions")
    question = Question(lesson_id=lesson_id, **payload.model_dump())
    db.add(question)
    await db.flush()
    return question


@router.get("/lessons/{lesson_id}/questions", response_model=Page[QuestionView])
async def list_questions(lesson_id: ResourceId, db: DB, limit: Limit = 20, offset: Offset = 0):
    await get_or_404(db, Lesson, lesson_id)
    return await page(
        db,
        select(Question)
        .where(Question.lesson_id == lesson_id)
        .order_by(Question.position, Question.id),
        limit,
        offset,
    )


@router.get("/questions/{question_id}", response_model=QuestionView)
async def read_question(question_id: ResourceId, db: DB):
    return await get_or_404(db, Question, question_id)


@router.put("/questions/{question_id}", response_model=QuestionView)
async def update_question(question_id: ResourceId, payload: QuestionWrite, db: DB):
    question = await get_or_404(db, Question, question_id)
    lesson = await get_or_404(db, Lesson, question.lesson_id)
    await editable_course(db, lesson.course_id)
    for key, value in payload.model_dump().items():
        setattr(question, key, value)
    await db.flush()
    return question


@router.delete("/questions/{question_id}", status_code=204)
async def delete_question(question_id: ResourceId, db: DB):
    question = await get_or_404(db, Question, question_id)
    lesson = await get_or_404(db, Lesson, question.lesson_id)
    await editable_course(db, lesson.course_id)
    await db.delete(question)
    return Response(status_code=204)
