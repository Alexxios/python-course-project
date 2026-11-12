import pytest
from anyio import to_thread
from sqlalchemy import select

from app.__main__ import main
from app.models import User

pytestmark = pytest.mark.anyio


async def test_migration_cli_uses_async_database(application, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", application.state.settings.database_url)
    await to_thread.run_sync(main, ["init-db"])
    async with application.state.sessions() as db:
        assert await db.scalar(select(User.id).limit(1)) is None
    assert "Database migrated to head." in capsys.readouterr().out
