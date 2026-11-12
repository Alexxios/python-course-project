import pytest

pytestmark = pytest.mark.anyio


async def test_current_profile(client, account_factory):
    identity, headers, _ = await account_factory()
    response = await client.get("/v1/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == identity
    assert response.json()["username"] == "student"
    assert "password" not in response.text
