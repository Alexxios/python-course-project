"""Health endpoints used by Kubernetes probes."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import User

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    # Keep liveness independent of databases and other external services.
    return {"status": "ok"}


@router.get("/ready")
def readiness(request: Request) -> dict[str, str]:
    if not request.app.state.ready:
        raise HTTPException(status_code=503, detail="Service is not ready")
    try:
        with request.app.state.sessions() as session:
            session.execute(select(User.id).limit(1))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable or schema not initialized") from exc
    return {"status": "ready"}
