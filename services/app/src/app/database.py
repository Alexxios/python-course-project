"""Async database connections and Alembic migrations for the API and CLI."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool


def create_database(url: str) -> AsyncEngine:
    parsed = make_url(url)
    options = {"pool_pre_ping": True}
    if parsed.get_backend_name() == "sqlite":
        parsed = parsed.set(drivername="sqlite+aiosqlite")
        options["connect_args"] = {"timeout": 5}
        if parsed.database in (None, "", ":memory:"):
            options["poolclass"] = StaticPool
    elif parsed.get_backend_name() == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
        options["connect_args"] = {"connect_timeout": 5}
    engine = create_async_engine(parsed, **options)
    if parsed.get_backend_name() == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def configure_sqlite(connection, _record):
            # SQLAlchemy owns BEGIN, including for transactional DDL and savepoints.
            # Enable foreign keys before opening a transaction.
            connection.isolation_level = None
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        @event.listens_for(engine.sync_engine, "begin")
        def begin_sqlite(connection):
            connection.exec_driver_sql("BEGIN")

    return engine


def migration_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    return config


async def upgrade_database(engine: AsyncEngine) -> None:
    def upgrade(connection: Connection) -> None:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    async with engine.begin() as connection:
        await connection.run_sync(upgrade)
