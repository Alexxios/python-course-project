import pytest


@pytest.fixture
async def practice_quiz(client, student_headers, learned_course):
    course, _, _ = learned_course
    response = await client.post(
        "/v1/me/practice-quizzes",
        headers=student_headers,
        json={"course_id": course["id"], "question_count": 5},
    )
    assert response.status_code == 201, response.text
    return response.json()
