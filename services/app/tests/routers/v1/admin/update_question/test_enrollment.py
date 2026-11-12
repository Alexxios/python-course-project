import pytest

pytestmark = pytest.mark.anyio


async def test_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "PUT",
            "/v1/admin" + f"/questions/{question['id']}",
            headers=admin_headers,
            json={"prompt": "x", "options": ["A", "B"], "correct_option": 1, "position": 1},
        )
    ).status_code == 409
