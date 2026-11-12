import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("threshold,passed", [(75, True), (76, False)])
async def test_passing_threshold_uses_the_exact_score(
    client, admin_headers, student_headers, course_factory, threshold, passed
):
    course, lessons, _ = await course_factory(published=False, with_test=False)
    answers = []
    for index in range(4):
        question = (
            await client.post(
                f"/v1/admin/lessons/{lessons[0]['id']}/questions",
                headers=admin_headers,
                json={
                    "prompt": f"Question {index}",
                    "options": ["A", "B"],
                    "correct_option": 0,
                    "position": index + 1,
                },
            )
        ).json()
        answers.append({"question_id": question["id"], "option": int(index == 3)})
    await client.put(
        f"/v1/admin/courses/{course['id']}",
        headers=admin_headers,
        json={"title": "Scoring", "passing_score": threshold, "published": True},
    )
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    response = await client.post(
        f"/v1/lessons/{lessons[0]['id']}/attempts",
        headers=student_headers,
        json={"answers": answers},
    )
    assert response.status_code == 201
    assert response.json()["score"] == 75
    assert response.json()["passed"] is passed
