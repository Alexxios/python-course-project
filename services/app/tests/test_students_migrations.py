from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.students.database import migration_config, upgrade_database
from app.students.models import Base


def test_migration_matches_models_and_can_be_reversed(student_engine):
    upgrade_database(student_engine)  # Repeated upgrades are harmless.
    with student_engine.begin() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        config = migration_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert "student_grades" not in inspect(connection).get_table_names()
    upgrade_database(student_engine)
    assert "student_grades" in inspect(student_engine).get_table_names()
