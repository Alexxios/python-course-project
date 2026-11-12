"""Database configuration and explicit Alembic schema upgrades."""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool


def database_url() -> str:
    return os.getenv("STUDENTS_DATABASE_URL", "sqlite:///students.sqlite3")


def create_database(url: str | None = None) -> Engine:
    parsed = make_url(url if url is not None else database_url())
    options = {}
    if parsed.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
        if parsed.database in (None, "", ":memory:"):
            options["poolclass"] = StaticPool
    return create_engine(parsed, **options)


def migration_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    return config


def upgrade_database(engine: Engine) -> None:
    """Apply migrations on the same connection, including for in-memory SQLite."""
    config = migration_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
