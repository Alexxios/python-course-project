import pytest
from sqlalchemy import update

from app.models import AuthSession, now

pytestmark = pytest.mark.anyio


async def test_expired_tokens_and_logout(client, application, account_factory):
    identity, headers, tokens = await account_factory()
    async with application.state.sessions.begin() as db:
        await db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == identity)
            .values(access_expires_at=now() - 1)
        )
    assert (await client.get("/v1/me", headers=headers)).status_code == 401
    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    replacement = response.json()
    headers = {"Authorization": f"Bearer {replacement['access_token']}"}
    assert (await client.post("/v1/auth/logout", headers=headers)).status_code == 204
    assert (await client.get("/v1/me", headers=headers)).status_code == 401
    assert (
        await client.post("/v1/auth/refresh", json={"refresh_token": replacement["refresh_token"]})
    ).status_code == 401
