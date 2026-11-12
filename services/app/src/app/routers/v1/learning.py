"""Public catalog and student course progression, assessments, and account views."""

from fastapi import APIRouter

from app.dependencies import CurrentUser
from app.schemas import (
    UserView,
)

router = APIRouter(tags=["learning"])


@router.get("/me", response_model=UserView, tags=["account"])
async def profile(user: CurrentUser):
    return user
