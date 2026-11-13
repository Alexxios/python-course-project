import pytest
from anyio import to_thread
from sqlalchemy import select

from app.__main__ import main
from app.models import User

pytestmark = pytest.mark.anyio


async def test_admin_cli_is_explicit_and_cannot_overwrite_accounts(
    application, monkeypatch, capsys
):
    monkeypatch.setenv("DATABASE_URL", application.state.settings.database_url)
    monkeypatch.setenv("LEARNING_ADMIN_PASSWORD", "a secure administrator password")
    await to_thread.run_sync(main, ["init-db"])
    args = ["create-admin", "--username", "owner", "--first-name", "Admin", "--last-name", "User"]
    await to_thread.run_sync(main, args)
    async with application.state.sessions() as db:
        user = await db.scalar(select(User).where(User.username == "owner"))
        assert user.role == "admin"
        original = user.password_hash
    with pytest.raises(SystemExit, match="1"):
        await to_thread.run_sync(main, args)
    async with application.state.sessions() as db:
        assert (
            await db.scalar(select(User.password_hash).where(User.username == "owner")) == original
        )
    output = capsys.readouterr()
    assert "already exists" in output.err
    assert "secure administrator password" not in output.out + output.err


async def test_cli_validates_password_without_echoing_it(application, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", application.state.settings.database_url)
    monkeypatch.setenv("LEARNING_ADMIN_PASSWORD", "short")
    with pytest.raises(SystemExit, match="1"):
        await to_thread.run_sync(
            main, ["create-admin", "--username", "admin", "--first-name", "A", "--last-name", "B"]
        )
    assert "12 to 128" in capsys.readouterr().err


async def test_migration_cli_uses_async_database(application, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", application.state.settings.database_url)
    await to_thread.run_sync(main, ["init-db"])
    async with application.state.sessions() as db:
        assert await db.scalar(select(User.id).limit(1)) is None
    assert "Database migrated to head." in capsys.readouterr().out
