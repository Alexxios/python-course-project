import pytest

pytestmark = pytest.mark.anyio


async def test_delete_cascades(client, admin_headers, draft_course):
    course, lessons, question = draft_course
    assert (
        await client.delete(f"/v1/admin/courses/{course['id']}", headers=admin_headers)
    ).status_code == 204
    assert (
        await client.get(f"/v1/admin/lessons/{lessons[0]['id']}", headers=admin_headers)
    ).status_code == 404
    assert (
        await client.get(f"/v1/admin/questions/{question['id']}", headers=admin_headers)
    ).status_code == 404
    assert (await client.get("/v1/admin/courses", headers=admin_headers)).json()["total"] == 0
