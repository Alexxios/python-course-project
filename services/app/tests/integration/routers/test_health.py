import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.anyio


async def test_liveness_responds_while_database_operation_waits(application, client):
    async with (
        application.state.engine.connect() as blocker,
        application.state.engine.connect() as waiter,
    ):
        pid = await waiter.scalar(text("SELECT pg_backend_pid()"))
        lock = text("SELECT pg_advisory_xact_lock(:key)")
        await blocker.execute(lock, {"key": pid})
        query = asyncio.create_task(waiter.execute(lock, {"key": pid}))
        waiting = text("SELECT EXISTS (SELECT 1 FROM pg_locks WHERE pid = :pid AND NOT granted)")
        try:
            async with asyncio.timeout(5):
                while not await blocker.scalar(waiting, {"pid": pid}):
                    await asyncio.sleep(0.01)
            response = await asyncio.wait_for(client.get("/health/live"), timeout=2)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            assert not query.done(), "SQL must still be waiting while HTTP responds"
        finally:
            await blocker.rollback()
            await asyncio.wait_for(query, timeout=5)


async def test_live(client):
    assert (await client.get("/health/live")).json() == {"status": "ok"}


async def test_missing_schema_fails_readiness_and_returns_safe_errors(application_factory):
    async with (
        application_factory(migrate=False) as app,
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.get("/health/live")).status_code == 200
        assert (await client.get("/health/ready")).status_code == 503


async def test_health_tracks_lifespan_and_database(application):
    assert application.state.ready is False
    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        assert (await client.get("/health/live")).json() == {"status": "ok"}
        assert (await client.get("/health/ready")).json() == {"status": "ready"}
        application.state.ready = False
        assert (await client.get("/health/ready")).status_code == 503
    assert application.state.ready is False
