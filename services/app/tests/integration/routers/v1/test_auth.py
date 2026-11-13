import asyncio
from threading import Event

import pytest
from anyio import to_thread
from sqlalchemy import select, update

from app.models import AuthSession, User, now
from app.security import PASSWORD_HASH, token_digest

pytestmark = pytest.mark.anyio


@pytest.fixture
def registration(password):
    return {"username": "student", "first_name": "Иван", "last_name": "Ли", "password": password}


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


async def test_password_verification_does_not_block_other_requests(
    client, account_factory, password, monkeypatch
):
    await account_factory()
    original_verify = PASSWORD_HASH.verify
    started = Event()
    release = Event()

    def slow_verify(*args, **kwargs):
        started.set()
        assert release.wait(5), "Password verification blocked the event loop"
        return original_verify(*args, **kwargs)

    monkeypatch.setattr(PASSWORD_HASH, "verify", slow_verify)
    login = asyncio.create_task(
        client.post("/v1/auth/login", json={"username": "student", "password": password})
    )
    try:
        assert await to_thread.run_sync(started.wait, 3)
        assert not login.done()
        response = await asyncio.wait_for(client.get("/health/live"), timeout=1)
        assert response.status_code == 200
    finally:
        release.set()
        response = await login
    assert response.status_code == 200


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


@pytest.mark.skip(reason="PostgreSQL row-lock coverage is deferred; service tests use SQLite")
async def test_simultaneous_refresh_is_single_use_on_postgresql(client, account_factory):
    _, _, tokens = await account_factory()
    start = asyncio.Event()

    async def refresh():
        await start.wait()
        response = await client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        return response.status_code

    tasks = [asyncio.create_task(refresh()) for _ in range(2)]
    start.set()
    async with asyncio.timeout(10):
        assert sorted(await asyncio.gather(*tasks)) == [200, 401]


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


@pytest.mark.parametrize(
    "body",
    [
        b'{"first_name":"\\ud800"}',
        b'{"\\udfff":1}',
        b'{"email":{"nested":"\\ud800"}}',
        b'{"first_name":NaN}',
        b'{"first_name":Infinity}',
        b'{"first_name":-Infinity}',
        b'{"first_name":1e999}',
        b"NaN",
        b'{"\\ud800":}',
    ],
)
async def test_unsafe_validation_input_returns_field_errors(client, body):
    response = await client.post(
        "/v1/auth/register", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"
    errors = response.json()["detail"]
    assert errors
    assert all(set(error) == {"loc", "msg", "type"} for error in errors)


@pytest.mark.parametrize("body", [b"\xff", b"\x00" * 21])
async def test_undecodable_request_body_returns_400(client, body):
    response = await client.post(
        "/v1/auth/register", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "There was an error parsing the body"}


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
