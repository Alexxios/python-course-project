import pytest

pytestmark = pytest.mark.anyio


async def test_private_course_list(client, student_headers, finished_course, account_factory):
    _, progress = finished_course
    assert (await client.get("/v1/me/courses", headers=student_headers)).json()["items"] == [
        progress
    ]
    _, other, _ = await account_factory("other")
    assert (await client.get("/v1/me/courses", headers=other)).json()["total"] == 0
