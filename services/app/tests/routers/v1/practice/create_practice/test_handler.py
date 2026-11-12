import pytest

pytestmark = pytest.mark.anyio


async def test_uses_only_completed_questions(client, student_headers, learned_course):
    course, lessons, _ = learned_course
    response = await client.post(
        "/v1/me/practice-quizzes",
        headers=student_headers,
        json={"course_id": course["id"], "question_count": 5},
    )
    assert response.status_code == 201
    quiz = response.json()
    assert quiz["source"] == "local" and len(quiz["questions"]) == 1
    assert quiz["questions"][0]["source_lesson_id"] == lessons[0]["id"]
    assert "correct_option" not in response.text
