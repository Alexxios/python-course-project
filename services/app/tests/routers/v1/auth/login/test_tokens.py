import pytest
from sqlalchemy import select

from app.models import AuthSession
from app.security import token_digest

pytestmark = pytest.mark.anyio


async def test_login_tokens(client, application, registration):
    assert (await client.post("/v1/auth/register", json=registration)).status_code == 201
    response = await client.post(
        "/v1/auth/login", json={"username": "STUDENT", "password": registration["password"]}
    )
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["access_token"] != tokens["refresh_token"]
    assert tokens["expires_in"] == 900
    async with application.state.sessions() as db:
        session = await db.scalar(select(AuthSession))
        assert session.access_hash == token_digest(tokens["access_token"])
        assert session.refresh_hash == token_digest(tokens["refresh_token"])
