"""Accept validated subscriber appeals and persist them before responding."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.models import AppealCreate, StoredAppeal
from app.storage import JsonAppealStore

router = APIRouter(prefix="/appeals", tags=["appeals"])
LOGGER = logging.getLogger(__name__)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StoredAppeal,
    responses={503: {"description": "The appeal could not be saved"}},
)
def create_appeal(appeal: AppealCreate, request: Request) -> StoredAppeal:
    """Save subscriber details, selected reasons, and the problem detection time."""
    stored = StoredAppeal(**appeal.model_dump())
    store: JsonAppealStore = request.app.state.appeal_store
    try:
        store.save(stored)
    except OSError as exc:
        LOGGER.exception("Could not save appeal")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The appeal could not be saved; please try again later",
        ) from exc
    return stored
