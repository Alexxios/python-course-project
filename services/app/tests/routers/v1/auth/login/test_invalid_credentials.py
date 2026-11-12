import pytest

pytestmark = pytest.mark.anyio


async def test_login_errors_are_indistinguishable(client, account_factory):
    await account_factory()
    known = await client.post(
        "/v1/auth/login", json={"username": "student", "password": "incorrect"}
    )
    unknown = await client.post(
        "/v1/auth/login", json={"username": "unknown", "password": "incorrect"}
    )
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json()
    assert known.headers["www-authenticate"] == "Bearer"
