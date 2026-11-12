import pytest

pytestmark = pytest.mark.anyio


async def test_live(client):
    assert (await client.get("/health/live")).json() == {"status": "ok"}
