import pytest

pytestmark = pytest.mark.anyio


async def test_private_progress(client, student_headers, learned_course, account_factory):
    course, _, _ = learned_course
    url = f"/v1/me/courses/{course['id']}/progress"
    assert (await client.get(url, headers=student_headers)).json()["progress_percent"] == 50
    _, other, _ = await account_factory("other")
    assert (await client.get(url, headers=other)).status_code == 403
