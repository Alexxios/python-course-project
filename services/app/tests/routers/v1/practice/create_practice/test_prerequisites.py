import pytest

pytestmark = pytest.mark.anyio


async def test_practice_requires_learned_material(client, student_headers, course_factory):
    course, lessons, _ = await course_factory(with_test=False)
    payload = {"course_id": course["id"]}
    assert (
        await client.post("/v1/me/practice-quizzes", headers=student_headers, json=payload)
    ).status_code == 403
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    assert (
        await client.post("/v1/me/practice-quizzes", headers=student_headers, json=payload)
    ).status_code == 409
    await client.post(f"/v1/lessons/{lessons[0]['id']}/complete", headers=student_headers)
    assert (
        await client.post("/v1/me/practice-quizzes", headers=student_headers, json=payload)
    ).status_code == 409
