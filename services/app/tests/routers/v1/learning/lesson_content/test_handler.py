import pytest

pytestmark = pytest.mark.anyio


async def test_enrollment_and_prerequisites(client, student_headers, course_factory):
    course, lessons, _ = await course_factory()
    assert (
        await client.get(f"/v1/lessons/{lessons[0]['id']}", headers=student_headers)
    ).status_code == 403
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    assert (
        await client.get(f"/v1/lessons/{lessons[1]['id']}", headers=student_headers)
    ).status_code == 403
    response = await client.get(f"/v1/lessons/{lessons[0]['id']}", headers=student_headers)
    assert response.json()["content"] == lessons[0]["content"]
    assert "correct_option" not in response.text


async def test_completed_content_remains_available_and_private(
    client, student_headers, learned_course, account_factory
):
    course, lessons, _ = learned_course
    assert (await client.get(f"/v1/lessons/{lessons[0]['id']}", headers=student_headers)).json()[
        "completed"
    ] is True
    assert (
        await client.get(f"/v1/lessons/{lessons[1]['id']}", headers=student_headers)
    ).status_code == 200
    _, other, _ = await account_factory("other")
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=other)
    assert (await client.get(f"/v1/lessons/{lessons[1]['id']}", headers=other)).status_code == 403
