"""Registration, authentication, refresh rotation, logout, and password changes."""

from fastapi import APIRouter, Request, Response
from sqlalchemy import delete, select
from starlette.concurrency import run_in_threadpool

from app.dependencies import DB, Auth, CurrentUser, unauthorized
from app.models import AuthSession, User, now
from app.schemas import ChangePassword, Login, Refresh, Register, Tokens, UserView
from app.security import DUMMY_HASH, PASSWORD_HASH, issue_tokens, token_digest

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserView, status_code=201)
async def register(payload: Register, db: DB) -> User:
    user = User(
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=(
            await run_in_threadpool(PASSWORD_HASH.hash, payload.password.get_secret_value())
        ),
        role="student",
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/login", response_model=Tokens)
async def login(payload: Login, db: DB, request: Request) -> Tokens:
    user = await db.scalar(select(User).where(User.username == payload.username).with_for_update())
    valid = await run_in_threadpool(
        PASSWORD_HASH.verify,
        payload.password.get_secret_value(),
        user.password_hash if user else DUMMY_HASH,
    )
    if not valid or user is None:
        raise unauthorized()
    return await issue_tokens(db, user, request.app.state.settings)


@router.post("/refresh", response_model=Tokens)
async def refresh(payload: Refresh, db: DB, request: Request) -> Tokens:
    digest = token_digest(payload.refresh_token)
    user_id = await db.scalar(select(AuthSession.user_id).where(AuthSession.refresh_hash == digest))
    if user_id is None:
        raise unauthorized()
    # Use the same user -> session lock order as login/password change. A refresh
    # racing with a password change must not recreate a revoked session.
    user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
    consumed = await db.scalar(
        delete(AuthSession)
        .where(
            AuthSession.refresh_hash == digest,
            AuthSession.refresh_expires_at > now(),
        )
        .returning(AuthSession.user_id)
    )
    if consumed is None or user is None:
        raise unauthorized()
    return await issue_tokens(db, user, request.app.state.settings)


@router.post("/logout", status_code=204)
async def logout(auth: Auth, db: DB) -> Response:
    await db.execute(delete(AuthSession).where(AuthSession.id == auth.id))
    return Response(status_code=204)


@router.post("/change-password", status_code=204)
async def change_password(payload: ChangePassword, user: CurrentUser, db: DB) -> Response:
    # Lock the user against concurrent logins before changing credentials.
    await db.refresh(user, with_for_update=True)
    if not (
        await run_in_threadpool(
            PASSWORD_HASH.verify, payload.current_password.get_secret_value(), user.password_hash
        )
    ):
        raise unauthorized()
    user.password_hash = await run_in_threadpool(
        PASSWORD_HASH.hash, payload.new_password.get_secret_value()
    )
    await db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    return Response(status_code=204)
