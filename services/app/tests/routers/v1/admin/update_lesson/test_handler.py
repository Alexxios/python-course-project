import pytest

pytestmark = pytest.mark.anyio


async def test_update(client, admin_headers, draft_course):
    _, lessons, _ = draft_course
    payload = {
        "title": "Updated",
        "description": "Details",
        "content": "Updated text",
        "position": 2,
        "video_url": "https://example.com/lesson.mp4",
    }
    response = await client.put(
        f"/v1/admin/lessons/{lessons[0]['id']}", headers=admin_headers, json=payload
    )
    assert response.status_code == 200
    assert response.json() == {**lessons[0], **payload}
