import pytest

pytestmark = pytest.mark.anyio


async def test_read_is_private(client, student_headers, practice_quiz, account_factory):
    url = f"/v1/me/practice-quizzes/{practice_quiz['id']}"
    assert (await client.get(url, headers=student_headers)).json() == practice_quiz
    _, other, _ = await account_factory("other")
    assert (await client.get(url, headers=other)).status_code == 404
