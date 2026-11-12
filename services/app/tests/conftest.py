import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from hypothesis import settings
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from app.config import Settings
from app.database import create_database, upgrade_database
from app.main import create_app

settings.register_profile("app", max_examples=30, deadline=None, print_blob=True)
settings.register_profile("fuzz", parent=settings.get_profile("app"), max_examples=1000)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "app"))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def application(tmp_path, anyio_backend):
    external_url = os.getenv("TEST_DATABASE_URL")
    if external_url:
        schema = "test_" + uuid4().hex
        admin_engine = create_database(external_url)
        async with admin_engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
        url = make_url(external_url).update_query_dict({"options": f"-csearch_path={schema}"})
        app = create_app(
            settings=Settings(
                database_url=url.render_as_string(hide_password=False), quiz_generator="local"
            )
        )
        try:
            await upgrade_database(app.state.engine)
            yield app
        finally:
            await app.state.engine.dispose()
            async with admin_engine.begin() as connection:
                await connection.execute(DropSchema(schema, cascade=True))
            await admin_engine.dispose()
        return
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
