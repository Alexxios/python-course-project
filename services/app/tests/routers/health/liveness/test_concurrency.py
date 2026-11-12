import asyncio
from threading import Event

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.anyio


async def test_liveness_responds_while_sqlite_operation_waits(tmp_path):
    # The SQL function runs in aiosqlite's worker, while HTTP uses the same event loop.
    started = Event()
    release = Event()

    def wait_for_release():
        started.set()
        return int(release.wait(timeout=10))

    app = create_app(settings=Settings(database_url=f"sqlite:///{tmp_path / 'waiting.db'}"))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        app.state.engine.connect() as connection,
    ):
        await connection.run_sync(
            lambda sync: sync.connection.create_function("wait_for_release", 0, wait_for_release)
        )
        query = asyncio.create_task(connection.execute(text("SELECT wait_for_release()")))
        try:
            assert await asyncio.to_thread(started.wait, 5), "SQL operation did not start"
            response = await asyncio.wait_for(client.get("/health/live"), timeout=2)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            assert not query.done(), "SQL must still be waiting while HTTP responds"
        finally:
            release.set()
            result = await asyncio.wait_for(query, timeout=5)
        assert result.scalar_one() == 1
