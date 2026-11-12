"""Session and migration setup, shared by the API and administrative CLI."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool


def create_database(url: str) -> Engine:
    parsed = make_url(url)
    options = {"pool_pre_ping": True}
    if parsed.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False, "timeout": 5, "autocommit": False}
        if parsed.database in (None, "", ":memory:"):
            options["poolclass"] = StaticPool
    elif parsed.get_backend_name() == "postgresql":
        options["connect_args"] = {"connect_timeout": 5}
    engine = create_engine(parsed, **options)
    if parsed.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            previous = connection.autocommit
            connection.autocommit = True
            connection.execute("PRAGMA foreign_keys=ON")
            connection.autocommit = previous

    return engine


def migration_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    return config


def upgrade_database(engine: Engine) -> None:
    config = migration_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
