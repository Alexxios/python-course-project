import pytest

pytestmark = pytest.mark.anyio


async def test_grading_is_private_single_use_and_does_not_change_progress(
    client, student_headers, practice_quiz, account_factory
):
    url = f"/v1/me/practice-quizzes/{practice_quiz['id']}/submit"
    payload = {"answers": [{"question_id": 1, "option": 0}]}
    _, other, _ = await account_factory("other")
    assert (await client.post(url, headers=other, json=payload)).status_code == 404
    response = await client.post(url, headers=student_headers, json=payload)
    assert response.status_code == 200 and response.json()["score"] == 100
    assert response.json()["submitted_at"] is not None
    assert "correct_option" not in response.text
    assert (await client.post(url, headers=student_headers, json=payload)).status_code == 409
    assert (
        await client.get(
            f"/v1/me/courses/{practice_quiz['course_id']}/progress", headers=student_headers
        )
    ).json()["progress_percent"] == 50
