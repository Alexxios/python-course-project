import pytest

pytestmark = pytest.mark.anyio


async def test_private_grade_history_and_filters(
    client, student_headers, learned_course, account_factory
):
    course, lessons, question = learned_course
    latest = (
        await client.post(
            f"/v1/lessons/{lessons[0]['id']}/attempts",
            headers=student_headers,
            json={"answers": [{"question_id": question["id"], "option": 1}]},
        )
    ).json()
    history = (
        await client.get(
            "/v1/me/attempts",
            headers=student_headers,
            params={"course_id": course["id"], "lesson_id": lessons[0]["id"], "limit": 1},
        )
    ).json()
    assert history["total"] == 2 and history["items"] == [latest]
    _, other, _ = await account_factory("other")
    assert (await client.get("/v1/me/attempts", headers=other)).json()["total"] == 0
