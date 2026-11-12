import pytest

pytestmark = pytest.mark.anyio


async def test_requires_administrator(client, student_headers):
    assert (await client.request("GET", "/v1/admin/courses")).status_code == 401
    assert (
        await client.request("GET", "/v1/admin/courses", headers=student_headers)
    ).status_code == 403
