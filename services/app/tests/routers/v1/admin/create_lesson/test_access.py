import pytest

pytestmark = pytest.mark.anyio


async def test_requires_administrator(client, student_headers):
    assert (await client.request("POST", "/v1/admin/courses/1/lessons")).status_code == 401
    assert (
        await client.request("POST", "/v1/admin/courses/1/lessons", headers=student_headers)
    ).status_code == 403
