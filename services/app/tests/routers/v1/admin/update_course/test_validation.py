import pytest

pytestmark = pytest.mark.anyio


async def test_publishing_requires_lessons(client, admin_headers):
    course = (
        await client.post("/v1/admin/courses", headers=admin_headers, json={"title": "Empty"})
    ).json()
    assert (
        await client.put(
            f"/v1/admin/courses/{course['id']}",
            headers=admin_headers,
            json={"title": "Empty", "published": True},
        )
    ).status_code == 409
