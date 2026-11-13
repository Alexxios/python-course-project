import pytest

pytestmark = pytest.mark.anyio


async def test_outline_marks_locked_lessons_without_content(
    client, student_headers, enrolled_course
):
    course, _, _ = enrolled_course
    result = (
        await client.get(f"/v1/courses/{course['id']}/lessons", headers=student_headers)
    ).json()
    assert [lesson["unlocked"] for lesson in result] == [True, False]
    assert "content" not in str(result)
