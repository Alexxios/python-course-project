import pytest
from sqlalchemy import select

from app.models import User

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "change",
    [
        {"role": "admin"},
        {"username": "x"},
        {"username": "a' OR 1=1"},
        {"username": "a" * 51},
        {"first_name": " "},
        {"last_name": "\x00"},
        {"password": "too short"},
        {"password": "x" * 129},
        {"password": None},
        {"password": True},
        {"first_name": "\ud800"},
        {"password": "long_surrogate_\ud800"},
    ],
)
async def test_invalid_registration_cannot_create_accounts(
    client, application, registration, change
):
    import json

    response = await client.post(
        "/v1/auth/register",
        content=json.dumps(registration | change),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    async with application.state.sessions() as db:
        assert await db.scalar(select(User.id)) is None
