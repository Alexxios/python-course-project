"""Argon2 password hashes and independently revocable opaque bearer tokens."""

import hashlib
import secrets

from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AuthSession, User, now
from app.schemas import Tokens

PASSWORD_HASH = PasswordHash.recommended()
# Equalize password verification work for unknown users without a stored credential.
DUMMY_HASH = PASSWORD_HASH.hash(secrets.token_urlsafe(32))


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_tokens(session: AsyncSession, user: User, settings: Settings) -> Tokens:
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(48)
    timestamp = now()
    session.add(
        AuthSession(
            user_id=user.id,
            access_hash=token_digest(access),
            refresh_hash=token_digest(refresh),
            access_expires_at=timestamp + settings.access_token_seconds,
            refresh_expires_at=timestamp + settings.refresh_token_seconds,
        )
    )
    await session.flush()
    return Tokens(
        access_token=access, refresh_token=refresh, expires_in=settings.access_token_seconds
    )
