import pytest

pytestmark = pytest.mark.anyio


async def test_password_change_revokes_every_session(client, account_factory, registration):
    _, headers, tokens = await account_factory()
    other = (
        await client.post(
            "/v1/auth/login", json={"username": "student", "password": registration["password"]}
        )
    ).json()
    payload = {"current_password": "incorrect", "new_password": "a new secure password"}
    assert (
        await client.post("/v1/auth/change-password", headers=headers, json=payload)
    ).status_code == 401
    assert (await client.get("/v1/me", headers=headers)).status_code == 200
    payload["current_password"] = registration["password"]
    assert (
        await client.post("/v1/auth/change-password", headers=headers, json=payload)
    ).status_code == 204
    for session in (tokens, other):
        assert (
            await client.get(
                "/v1/me", headers={"Authorization": f"Bearer {session['access_token']}"}
            )
        ).status_code == 401
        assert (
            await client.post("/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
        ).status_code == 401
    assert (
        await client.post(
            "/v1/auth/login", json={"username": "student", "password": registration["password"]}
        )
    ).status_code == 401
    assert (
        await client.post(
            "/v1/auth/login", json={"username": "student", "password": payload["new_password"]}
        )
    ).status_code == 200
