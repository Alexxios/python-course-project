import pytest
from sqlalchemy import update

from app.models import AuthSession, now

pytestmark = pytest.mark.anyio


async def test_expired_refresh_token(client, application, account_factory):
    identity, _, tokens = await account_factory()
    async with application.state.sessions.begin() as db:
        await db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == identity)
            .values(refresh_expires_at=now() - 1)
        )
    assert (
        await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).status_code == 401
