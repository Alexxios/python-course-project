import asyncio
from threading import Event

import pytest
from anyio import to_thread

from app.security import PASSWORD_HASH

pytestmark = pytest.mark.anyio


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
