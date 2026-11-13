import pytest

pytestmark = pytest.mark.anyio


async def test_cannot_skip_lessons_or_bypass_a_test(client, student_headers, enrolled_course):
    _, lessons, _ = enrolled_course
    assert (
        await client.post(f"/v1/lessons/{lessons[1]['id']}/complete", headers=student_headers)
    ).status_code == 403
    assert (
        await client.post(f"/v1/lessons/{lessons[0]['id']}/complete", headers=student_headers)
    ).status_code == 409


async def test_completion_is_idempotent(client, student_headers, learned_course):
    _, lessons, _ = learned_course
    url = f"/v1/lessons/{lessons[1]['id']}/complete"
    finished = (await client.post(url, headers=student_headers)).json()
    assert finished["progress_percent"] == 100 and finished["next_lesson_id"] is None
    assert (await client.post(url, headers=student_headers)).json() == finished
