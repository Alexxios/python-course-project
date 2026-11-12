import pytest

pytestmark = pytest.mark.anyio


async def test_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "PUT",
            "/v1/admin" + f"/lessons/{lessons[0]['id']}",
            headers=admin_headers,
            json={"title": "Changed", "content": "x", "position": 1},
        )
    ).status_code == 409
