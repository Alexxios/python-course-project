import pytest

pytestmark = pytest.mark.anyio


async def test_list(client, admin_headers, draft_course):
    course, _, _ = draft_course
    result = (await client.get("/v1/admin/courses", headers=admin_headers)).json()
    assert result["items"] == [course] and result["total"] == 1
