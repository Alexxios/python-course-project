import pytest

from app.models import User
from app.security import PASSWORD_HASH

pytestmark = pytest.mark.anyio


async def test_register(client, application, registration):
    response = await client.post("/v1/auth/register", json={**registration, "username": "STUDENT"})
    assert response.status_code == 201
    user = response.json()
    assert user["username"] == "student"
    assert user["role"] == "student"
    assert "password" not in response.text
    assert (await client.post("/v1/auth/register", json=registration)).status_code == 409
    async with application.state.sessions() as db:
        stored = await db.get(User, user["id"])
        assert stored.password_hash.startswith("$argon2id$")
        assert PASSWORD_HASH.verify(registration["password"], stored.password_hash)
