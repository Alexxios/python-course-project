import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("kind", ["missing", "extra", "duplicate", "invalid_option", "boolean"])
async def test_invalid_answers_never_record_attempts(client, student_headers, course_factory, kind):
    course, lessons, question = await course_factory()
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    answers = [{"question_id": question["id"], "option": 0}]
    if kind == "missing":
        answers = []
    elif kind == "extra":
        answers.append({"question_id": 9999, "option": 0})
    elif kind == "duplicate":
        answers *= 2
    else:
        answers[0]["option"] = 5 if kind == "invalid_option" else True
    response = await client.post(
        f"/v1/lessons/{lessons[0]['id']}/attempts",
        headers=student_headers,
        json={"answers": answers},
    )
    assert response.status_code == 422
    assert (await client.get("/v1/me/attempts", headers=student_headers)).json()["total"] == 0
