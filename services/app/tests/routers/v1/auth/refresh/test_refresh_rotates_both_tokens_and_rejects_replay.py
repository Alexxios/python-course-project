import pytest

pytestmark = pytest.mark.anyio


async def test_refresh_rotates_both_tokens_and_rejects_replay(client, account_factory):
    _, headers, tokens = await account_factory()
    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    replacement = response.json()
    assert replacement["access_token"] != tokens["access_token"]
    assert replacement["refresh_token"] != tokens["refresh_token"]
    assert (await client.get("/v1/me", headers=headers)).status_code == 401
    assert (
        await client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).status_code == 401
    assert (
        await client.get(
            "/v1/me", headers={"Authorization": f"Bearer {replacement['access_token']}"}
        )
    ).status_code == 200
    assert (
        await client.get(
            "/v1/me", headers={"Authorization": f"Bearer {replacement['refresh_token']}"}
        )
    ).status_code == 401
    assert (
        await client.post("/v1/auth/refresh", json={"refresh_token": replacement["access_token"]})
    ).status_code == 401
