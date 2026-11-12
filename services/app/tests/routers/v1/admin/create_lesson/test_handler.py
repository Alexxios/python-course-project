import pytest

pytestmark = pytest.mark.anyio


async def test_create_and_reject_duplicate_position(client, admin_headers, draft_course):
    course, _, _ = draft_course
    url = f"/v1/admin/courses/{course['id']}/lessons"
    body = {"title": "Intro", "content": "Lesson text", "position": 30}
    response = await client.post(url, headers=admin_headers, json=body)
    assert response.status_code == 201
    assert response.json()["content"] == body["content"]
    assert (await client.post(url, headers=admin_headers, json=body)).status_code == 409
