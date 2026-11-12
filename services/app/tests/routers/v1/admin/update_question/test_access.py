import pytest

pytestmark = pytest.mark.anyio


async def test_requires_administrator(client, student_headers):
    assert (await client.request("PUT", "/v1/admin/questions/1")).status_code == 401
    assert (
        await client.request("PUT", "/v1/admin/questions/1", headers=student_headers)
    ).status_code == 403
