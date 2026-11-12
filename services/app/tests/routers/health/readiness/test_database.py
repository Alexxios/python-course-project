import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.anyio


async def test_missing_schema_fails_readiness_and_returns_safe_errors(tmp_path):
    app = create_app(settings=Settings(database_url=f"sqlite:///{tmp_path / 'missing.db'}"))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.get("/health/live")).status_code == 200
        assert (await client.get("/health/ready")).status_code == 503
