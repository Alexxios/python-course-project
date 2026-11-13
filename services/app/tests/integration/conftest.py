from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema
from testcontainers.community.postgres import PostgresContainer

from app.config import Settings
from app.database import create_database, upgrade_database
from app.main import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def postgres_url():
    compose_path = Path(__file__).resolve().parents[4] / "infra" / "docker-compose.yml"
    compose = yaml.safe_load(compose_path.read_text())
    image = compose["services"]["postgres"]["image"]
    with PostgresContainer(
        image, driver="psycopg", username="test", password="test", dbname="test"
    ) as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def application_factory(postgres_url):
    @asynccontextmanager
    async def create(*, migrate=True):
        # Each call also isolates a Hypothesis example on its own asyncio loop.
        schema = "test_" + uuid4().hex
        admin_engine = create_database(postgres_url)
        try:
            async with admin_engine.begin() as connection:
                await connection.execute(CreateSchema(schema))
            try:
                url = make_url(postgres_url).update_query_dict(
                    {"options": f"-csearch_path={schema}"}
                )
                app = create_app(
                    settings=Settings(
                        database_url=url.render_as_string(hide_password=False),
                        quiz_generator="local",
                    )
                )
                try:
                    if migrate:
                        await upgrade_database(app.state.engine)
                    yield app
                finally:
                    await app.state.engine.dispose()
            finally:
                async with admin_engine.begin() as connection:
                    await connection.execute(DropSchema(schema, cascade=True))
        finally:
            await admin_engine.dispose()

    return create


@pytest.fixture
async def application(application_factory, anyio_backend):
    async with application_factory() as app:
        yield app


@pytest.fixture
async def client(application):
    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        yield client
