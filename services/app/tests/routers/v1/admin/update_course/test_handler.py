import pytest

pytestmark = pytest.mark.anyio


async def test_publish(client, admin_headers, draft_course):
    course, _, _ = draft_course
    response = await client.put(
        f"/v1/admin/courses/{course['id']}",
        headers=admin_headers,
        json={"title": "Published", "published": True},
    )
    assert response.status_code == 200
    assert response.json()["published"] is True
    assert response.json()["title"] == "Published"
