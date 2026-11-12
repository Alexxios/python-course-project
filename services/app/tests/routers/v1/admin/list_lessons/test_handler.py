import pytest

pytestmark = pytest.mark.anyio


async def test_list(client, admin_headers, draft_course):
    course, lessons, _ = draft_course
    assert (
        await client.get(f"/v1/admin/courses/{course['id']}/lessons", headers=admin_headers)
    ).json()["items"] == lessons
