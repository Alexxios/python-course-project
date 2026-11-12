import pytest

pytestmark = pytest.mark.anyio


async def test_grades_retries_and_unlocks_next_lesson(client, student_headers, enrolled_course):
    course, lessons, question = enrolled_course
    url = f"/v1/lessons/{lessons[0]['id']}/attempts"
    payload = {"answers": [{"question_id": question["id"], "option": 1}]}
    wrong = await client.post(url, headers=student_headers, json=payload)
    assert wrong.status_code == 201
    assert wrong.json()["score"] == 0 and wrong.json()["passed"] is False
    assert (
        await client.get(f"/v1/lessons/{lessons[1]['id']}", headers=student_headers)
    ).status_code == 403
    payload["answers"][0]["option"] = 0
    passed = (await client.post(url, headers=student_headers, json=payload)).json()
    assert passed["passed"] is True and passed["score"] == 100
    progress = (
        await client.get(f"/v1/me/courses/{course['id']}/progress", headers=student_headers)
    ).json()
    assert progress["progress_percent"] == 50 and progress["next_lesson_id"] == lessons[1]["id"]
