import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.anyio


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
