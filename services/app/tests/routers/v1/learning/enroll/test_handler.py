import pytest

pytestmark = pytest.mark.anyio


async def test_enroll_once(client, student_headers, course_factory):
    course, _, _ = await course_factory()
    url = f"/v1/courses/{course['id']}/enroll"
    response = await client.post(url, headers=student_headers)
    assert response.status_code == 201
    assert response.json()["progress_percent"] == 0
    assert (await client.post(url, headers=student_headers)).status_code == 409


async def test_cannot_enroll_in_a_draft(client, student_headers, course_factory):
    course, _, _ = await course_factory(published=False)
    assert (
        await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    ).status_code == 404
