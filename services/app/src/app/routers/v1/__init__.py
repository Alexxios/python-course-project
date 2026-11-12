"""API v1 router composition and shared response documentation."""

from fastapi import APIRouter

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
