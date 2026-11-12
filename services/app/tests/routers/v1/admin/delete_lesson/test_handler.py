import pytest

pytestmark = pytest.mark.anyio


async def test_delete(client, admin_headers, draft_course):
    _, lessons, _ = draft_course
    url = f"/v1/admin/lessons/{lessons[0]['id']}"
    assert (await client.delete(url, headers=admin_headers)).status_code == 204
    assert (await client.get(url, headers=admin_headers)).status_code == 404


async def test_last_published_lesson_cannot_be_deleted(client, admin_headers, course_factory):
    _, lessons, _ = await course_factory()
    assert (
        await client.delete(f"/v1/admin/lessons/{lessons[0]['id']}", headers=admin_headers)
    ).status_code == 204
    assert (
        await client.delete(f"/v1/admin/lessons/{lessons[1]['id']}", headers=admin_headers)
    ).status_code == 409
