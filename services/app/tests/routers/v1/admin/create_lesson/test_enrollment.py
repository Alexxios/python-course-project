import pytest

pytestmark = pytest.mark.anyio


async def test_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "POST",
            "/v1/admin" + f"/courses/{course['id']}/lessons",
            headers=admin_headers,
            json={"title": "New", "content": "x", "position": 30},
        )
    ).status_code == 409
