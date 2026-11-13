import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.database import upgrade_database
from app.main import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def application(tmp_path, anyio_backend):
    app = create_app(
        settings=Settings(
            database_url=f"sqlite:///{tmp_path / 'learning.sqlite3'}", quiz_generator="local"
        )
    )
    try:
        await upgrade_database(app.state.engine)
        yield app
    finally:
        await app.state.engine.dispose()


@pytest.fixture
async def client(application):
    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        yield client
