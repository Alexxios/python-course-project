import pytest

pytestmark = pytest.mark.anyio


async def test_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "POST",
            "/v1/admin" + f"/lessons/{lessons[0]['id']}/questions",
            headers=admin_headers,
            json={"prompt": "x", "options": ["A", "B"], "correct_option": 0, "position": 2},
        )
    ).status_code == 409
