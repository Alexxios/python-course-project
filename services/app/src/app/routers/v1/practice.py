"""Private generated quizzes are separate from course completion assessments."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select, update

from app.dependencies import DB, CurrentUser, Limit, Offset, ResourceId, page
from app.learning import grade_answers
from app.models import PracticeQuiz, now
from app.practice import generate_practice, practice_view
from app.schemas import Page, PracticeRequest, PracticeView, Submission

router = APIRouter(prefix="/me/practice-quizzes", tags=["personalized practice"])


async def owned_quiz(db, user_id: int, quiz_id: int) -> PracticeQuiz:
    quiz = await db.scalar(
        select(PracticeQuiz).where(PracticeQuiz.id == quiz_id, PracticeQuiz.user_id == user_id)
    )
    if quiz is None:
        raise HTTPException(404, "Practice quiz not found")
    return quiz


@router.post("", response_model=PracticeView, status_code=201)
async def create_practice(payload: PracticeRequest, user: CurrentUser, db: DB, request: Request):
    return practice_view(
        await generate_practice(
            db, user.id, payload.course_id, payload.question_count, request.app.state.settings
        )
    )


@router.get("", response_model=Page[PracticeView])
async def my_practice(user: CurrentUser, db: DB, limit: Limit = 20, offset: Offset = 0):
    result = await page(
        db,
        select(PracticeQuiz)
        .where(PracticeQuiz.user_id == user.id)
        .order_by(PracticeQuiz.id.desc()),
        limit,
        offset,
    )
    result["items"] = [practice_view(quiz) for quiz in result["items"]]
    return result


@router.get("/{quiz_id}", response_model=PracticeView)
async def get_practice(quiz_id: ResourceId, user: CurrentUser, db: DB):
    return practice_view(await owned_quiz(db, user.id, quiz_id))


@router.post("/{quiz_id}/submit", response_model=PracticeView)
async def submit_practice(quiz_id: ResourceId, payload: Submission, user: CurrentUser, db: DB):
    quiz = await owned_quiz(db, user.id, quiz_id)
    _, score = grade_answers(quiz.questions, payload)
    result = await db.execute(
        update(PracticeQuiz)
        .where(PracticeQuiz.id == quiz.id, PracticeQuiz.submitted_at.is_(None))
        .values(score=score, submitted_at=now(), answers=payload.model_dump()["answers"])
    )
    if result.rowcount != 1:
        raise HTTPException(409, "This practice quiz has already been submitted")
    await db.refresh(quiz)
    return practice_view(quiz)
