import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.database import migration_config, upgrade_database
from app.models import Base

pytestmark = pytest.mark.anyio


async def test_migrations_match_models_and_reverse(application):
    engine = application.state.engine
    await upgrade_database(engine)

    def check_and_downgrade(connection):
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        config = migration_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert inspect(connection).get_table_names() == ["alembic_version"]

    async with engine.begin() as connection:
        await connection.run_sync(check_and_downgrade)
    await upgrade_database(engine)
    async with engine.connect() as connection:
        tables = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
    assert "users" in tables
