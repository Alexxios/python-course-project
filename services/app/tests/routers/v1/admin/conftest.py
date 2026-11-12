import pytest

from app.models import Enrollment


@pytest.fixture
async def draft_course(course_factory):
    return await course_factory(published=False)


@pytest.fixture
async def enrolled_course(draft_course, application, account_factory):
    course, _, _ = draft_course
    identity, _, _ = await account_factory("enrolled")
    async with application.state.sessions.begin() as db:
        db.add(Enrollment(user_id=identity, course_id=course["id"]))
    return draft_course


@pytest.fixture
def question_payload():
    return {"prompt": "What?", "options": ["A", "B"], "correct_option": 0, "position": 1}
