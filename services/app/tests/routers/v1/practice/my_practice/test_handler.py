import pytest

pytestmark = pytest.mark.anyio


async def test_list_is_private(client, student_headers, practice_quiz, account_factory):
    assert (await client.get("/v1/me/practice-quizzes", headers=student_headers)).json()[
        "items"
    ] == [practice_quiz]
    _, other, _ = await account_factory("other")
    assert (await client.get("/v1/me/practice-quizzes", headers=other)).json()["total"] == 0
