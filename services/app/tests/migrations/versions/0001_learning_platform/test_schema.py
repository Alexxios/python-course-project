from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.database import migration_config, upgrade_database
from app.models import Base


def test_migrations_match_models_and_reverse(application):
    engine = application.state.engine
    upgrade_database(engine)
    with engine.begin() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        config = migration_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert inspect(connection).get_table_names() == ["alembic_version"]
    upgrade_database(engine)
    assert "users" in inspect(engine).get_table_names()
