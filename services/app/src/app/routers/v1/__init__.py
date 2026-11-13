"""API v1 router composition and shared response documentation."""

from fastapi import APIRouter

from app.routers.v1.admin import router as admin_router
from app.routers.v1.auth import router as auth_router
from app.routers.v1.learning import router as learning_router
from app.routers.v1.practice import router as practice_router

router = APIRouter(
    prefix="/v1",
    responses={
        400: {"description": "Undecodable request body"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient access or lesson locked"},
        404: {"description": "Resource not found"},
        409: {"description": "Duplicate resource or invalid state transition"},
        502: {"description": "AI generation failed"},
        503: {"description": "Database or configured service unavailable"},
    },
)
for child_router in (auth_router, admin_router, learning_router, practice_router):
    router.include_router(child_router)
