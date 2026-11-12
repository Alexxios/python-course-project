import asyncio

import pytest

pytestmark = pytest.mark.anyio


async def test_simultaneous_refresh_is_single_use_on_postgresql(
    client, application, account_factory
):
    if application.state.engine.dialect.name != "postgresql":
        pytest.skip("Concurrent transaction test uses PostgreSQL row locks")
    _, _, tokens = await account_factory()
    start = asyncio.Event()

    async def refresh():
        await start.wait()
        response = await client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        return response.status_code

    tasks = [asyncio.create_task(refresh()) for _ in range(2)]
    start.set()
    async with asyncio.timeout(10):
        assert sorted(await asyncio.gather(*tasks)) == [200, 401]
