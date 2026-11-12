import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.anyio


async def test_database_error_is_safe(tmp_path):
    app = create_app(settings=Settings(database_url=f"sqlite:///{tmp_path / 'missing.db'}"))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
    ):
        response = await client.get("/v1/courses")
        assert response.status_code == 503
        assert str(tmp_path) not in response.text
