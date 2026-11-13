import pytest

pytestmark = pytest.mark.anyio


async def test_no_test_lessons_use_completion_endpoint(client, student_headers, course_factory):
    course, lessons, _ = await course_factory(with_test=False)
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    assert (
        await client.post(
            f"/v1/lessons/{lessons[0]['id']}/attempts",
            headers=student_headers,
            json={"answers": [{"question_id": 1, "option": 0}]},
        )
    ).status_code == 409
    assert (
        await client.post(f"/v1/lessons/{lessons[0]['id']}/complete", headers=student_headers)
    ).json()["progress_percent"] == 50
