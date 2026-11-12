import pytest

pytestmark = pytest.mark.anyio


async def test_read(client, admin_headers, draft_course):
    course, _, _ = draft_course
    assert (
        await client.get(f"/v1/admin/courses/{course['id']}", headers=admin_headers)
    ).json() == course
