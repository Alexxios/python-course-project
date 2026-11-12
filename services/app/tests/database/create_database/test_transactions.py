import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Lesson, User

pytestmark = pytest.mark.anyio


def user(username):
    return User(
        username=username,
        first_name="Test",
        last_name="User",
        password_hash="test-hash",
    )


async def test_failed_transaction_rolls_back_flushed_changes(application):
    with pytest.raises(RuntimeError, match="abort transaction"):
        async with application.state.sessions.begin() as session:
            session.add(user("rolled_back"))
            await session.flush()
            raise RuntimeError("abort transaction")

    async with application.state.sessions() as session:
        assert await session.scalar(select(User.id)) is None


async def test_savepoint_rollback_preserves_outer_transaction(application):
    async with application.state.sessions.begin() as session:
        session.add(user("retained"))
        await session.flush()
        with pytest.raises(RuntimeError, match="abort savepoint"):
            async with session.begin_nested():
                session.add(user("rolled_back"))
                await session.flush()
                raise RuntimeError("abort savepoint")

    async with application.state.sessions() as session:
        assert list(await session.scalars(select(User.username))) == ["retained"]


async def test_foreign_keys_reject_orphan_lessons(application):
    with pytest.raises(IntegrityError):
        async with application.state.sessions.begin() as session:
            session.add(
                Lesson(
                    course_id=2147483647,
                    title="Orphan",
                    description="",
                    content="No parent course exists.",
                    position=1,
                )
            )
            await session.flush()


async def test_schema_changes_are_transactional(application):
    async with application.state.engine.connect() as connection:
        transaction = await connection.begin()
        await connection.execute(text("CREATE TABLE rollback_probe (id INTEGER PRIMARY KEY)"))
        await transaction.rollback()
        tables = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
    assert "rollback_probe" not in tables
