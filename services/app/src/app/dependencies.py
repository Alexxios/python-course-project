"""Per-request transactions, authentication, authorization, and pagination."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthSession, User, now
from app.security import token_digest

bearer = HTTPBearer(auto_error=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessions.begin() as session:
        yield session


DB = Annotated[AsyncSession, Depends(get_session, scope="function")]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=2147483647)]
ResourceId = Annotated[int, Path(ge=1, le=2147483647)]
FilterId = Annotated[int, Query(ge=1, le=2147483647)]


def unauthorized() -> HTTPException:
    return HTTPException(
        401, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"}
    )


async def get_auth_session(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> AuthSession:
    if credentials is None or len(credentials.credentials) > 256:
        raise unauthorized()
    auth = await db.scalar(
        select(AuthSession).where(
            AuthSession.access_hash == token_digest(credentials.credentials),
            AuthSession.access_expires_at > now(),
        )
    )
    if auth is None:
        raise unauthorized()
    return auth


Auth = Annotated[AuthSession, Depends(get_auth_session)]


async def get_user(db: DB, auth: Auth) -> User:
    user = await db.get(User, auth.user_id)
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


Admin = Annotated[User, Depends(require_admin)]


async def get_or_404(db: AsyncSession, model, identity: int):
    record = await db.get(model, identity)
    if record is None:
        raise HTTPException(404, "Resource not found")
    return record


async def page(db: AsyncSession, statement, limit: int, offset: int) -> dict:
    total = await db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    return {
        "items": list(await db.scalars(statement.limit(limit).offset(offset))),
        "total": total,
        "limit": limit,
        "offset": offset,
    }
