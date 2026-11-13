import pytest

from app.models import Enrollment

pytestmark = pytest.mark.anyio


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


async def test_create_course_requires_administrator(client, student_headers):
    assert (await client.request("POST", "/v1/admin/courses")).status_code == 401
    assert (
        await client.request("POST", "/v1/admin/courses", headers=student_headers)
    ).status_code == 403


async def test_create_course(client, admin_headers):
    response = await client.post(
        "/v1/admin/courses", headers=admin_headers, json={"title": "Draft"}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Draft"
    assert response.json()["published"] is False


async def test_create_lesson_requires_administrator(client, student_headers):
    assert (await client.request("POST", "/v1/admin/courses/1/lessons")).status_code == 401
    assert (
        await client.request("POST", "/v1/admin/courses/1/lessons", headers=student_headers)
    ).status_code == 403


async def test_create_lesson_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "POST",
            "/v1/admin" + f"/courses/{course['id']}/lessons",
            headers=admin_headers,
            json={"title": "New", "content": "x", "position": 30},
        )
    ).status_code == 409


async def test_create_and_reject_duplicate_position(client, admin_headers, draft_course):
    course, _, _ = draft_course
    url = f"/v1/admin/courses/{course['id']}/lessons"
    body = {"title": "Intro", "content": "Lesson text", "position": 30}
    response = await client.post(url, headers=admin_headers, json=body)
    assert response.status_code == 201
    assert response.json()["content"] == body["content"]
    assert (await client.post(url, headers=admin_headers, json=body)).status_code == 409


async def test_create_question_requires_administrator(client, student_headers):
    assert (await client.request("POST", "/v1/admin/lessons/1/questions")).status_code == 401
    assert (
        await client.request("POST", "/v1/admin/lessons/1/questions", headers=student_headers)
    ).status_code == 403


async def test_create_question_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "POST",
            "/v1/admin" + f"/lessons/{lessons[0]['id']}/questions",
            headers=admin_headers,
            json={"prompt": "x", "options": ["A", "B"], "correct_option": 0, "position": 2},
        )
    ).status_code == 409


async def test_create_question(client, admin_headers, draft_course, question_payload):
    _, lessons, _ = draft_course
    payload = {**question_payload, "position": 2}
    response = await client.post(
        f"/v1/admin/lessons/{lessons[0]['id']}/questions", headers=admin_headers, json=payload
    )
    assert response.status_code == 201
    assert all((response.json()[key] == value for key, value in payload.items()))


@pytest.mark.parametrize(
    "changes",
    [
        {"options": ["same", "same"]},
        {"options": ["only"]},
        {"correct_option": 2},
        {"correct_option": True},
        {"position": 0},
        {"prompt": " "},
        {"options": ["x"] * 7},
    ],
)
async def test_invalid_test_definitions(client, admin_headers, course_factory, changes):
    _, lessons, _ = await course_factory(published=False, with_test=False)
    payload = {"prompt": "Question", "options": ["A", "B"], "correct_option": 0, "position": 1}
    assert (
        await client.post(
            f"/v1/admin/lessons/{lessons[0]['id']}/questions",
            headers=admin_headers,
            json=payload | changes,
        )
    ).status_code == 422


async def test_delete_course_requires_administrator(client, student_headers):
    assert (await client.request("DELETE", "/v1/admin/courses/1")).status_code == 401
    assert (
        await client.request("DELETE", "/v1/admin/courses/1", headers=student_headers)
    ).status_code == 403


async def test_delete_course_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "DELETE", "/v1/admin" + f"/courses/{course['id']}", headers=admin_headers, json=None
        )
    ).status_code == 409


async def test_delete_cascades(client, admin_headers, draft_course):
    course, lessons, question = draft_course
    assert (
        await client.delete(f"/v1/admin/courses/{course['id']}", headers=admin_headers)
    ).status_code == 204
    assert (
        await client.get(f"/v1/admin/lessons/{lessons[0]['id']}", headers=admin_headers)
    ).status_code == 404
    assert (
        await client.get(f"/v1/admin/questions/{question['id']}", headers=admin_headers)
    ).status_code == 404
    assert (await client.get("/v1/admin/courses", headers=admin_headers)).json()["total"] == 0


async def test_delete_lesson_requires_administrator(client, student_headers):
    assert (await client.request("DELETE", "/v1/admin/lessons/1")).status_code == 401
    assert (
        await client.request("DELETE", "/v1/admin/lessons/1", headers=student_headers)
    ).status_code == 403


async def test_delete_lesson_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "DELETE", "/v1/admin" + f"/lessons/{lessons[0]['id']}", headers=admin_headers, json=None
        )
    ).status_code == 409


async def test_delete_lesson(client, admin_headers, draft_course):
    _, lessons, _ = draft_course
    url = f"/v1/admin/lessons/{lessons[0]['id']}"
    assert (await client.delete(url, headers=admin_headers)).status_code == 204
    assert (await client.get(url, headers=admin_headers)).status_code == 404


async def test_last_published_lesson_cannot_be_deleted(client, admin_headers, course_factory):
    _, lessons, _ = await course_factory()
    assert (
        await client.delete(f"/v1/admin/lessons/{lessons[0]['id']}", headers=admin_headers)
    ).status_code == 204
    assert (
        await client.delete(f"/v1/admin/lessons/{lessons[1]['id']}", headers=admin_headers)
    ).status_code == 409


async def test_delete_question_requires_administrator(client, student_headers):
    assert (await client.request("DELETE", "/v1/admin/questions/1")).status_code == 401
    assert (
        await client.request("DELETE", "/v1/admin/questions/1", headers=student_headers)
    ).status_code == 403


async def test_delete_question_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "DELETE", "/v1/admin" + f"/questions/{question['id']}", headers=admin_headers, json=None
        )
    ).status_code == 409


async def test_delete_question(client, admin_headers, draft_course):
    _, _, question = draft_course
    url = f"/v1/admin/questions/{question['id']}"
    assert (await client.delete(url, headers=admin_headers)).status_code == 204
    assert (await client.get(url, headers=admin_headers)).status_code == 404


async def test_list_courses_requires_administrator(client, student_headers):
    assert (await client.request("GET", "/v1/admin/courses")).status_code == 401
    assert (
        await client.request("GET", "/v1/admin/courses", headers=student_headers)
    ).status_code == 403


async def test_list_courses(client, admin_headers, draft_course):
    course, _, _ = draft_course
    result = (await client.get("/v1/admin/courses", headers=admin_headers)).json()
    assert result["items"] == [course] and result["total"] == 1


async def test_list_lessons_requires_administrator(client, student_headers):
    assert (await client.request("GET", "/v1/admin/courses/1/lessons")).status_code == 401
    assert (
        await client.request("GET", "/v1/admin/courses/1/lessons", headers=student_headers)
    ).status_code == 403


async def test_list_lessons(client, admin_headers, draft_course):
    course, lessons, _ = draft_course
    assert (
        await client.get(f"/v1/admin/courses/{course['id']}/lessons", headers=admin_headers)
    ).json()["items"] == lessons


async def test_list_questions_requires_administrator(client, student_headers):
    assert (await client.request("GET", "/v1/admin/lessons/1/questions")).status_code == 401
    assert (
        await client.request("GET", "/v1/admin/lessons/1/questions", headers=student_headers)
    ).status_code == 403


async def test_list_questions(client, admin_headers, draft_course):
    _, lessons, question = draft_course
    assert (
        await client.get(f"/v1/admin/lessons/{lessons[0]['id']}/questions", headers=admin_headers)
    ).json()["items"] == [question]


async def test_read_course_requires_administrator(client, student_headers):
    assert (await client.request("GET", "/v1/admin/courses/1")).status_code == 401
    assert (
        await client.request("GET", "/v1/admin/courses/1", headers=student_headers)
    ).status_code == 403


async def test_read_course(client, admin_headers, draft_course):
    course, _, _ = draft_course
    assert (
        await client.get(f"/v1/admin/courses/{course['id']}", headers=admin_headers)
    ).json() == course


async def test_read_lesson_requires_administrator(client, student_headers):
    assert (await client.request("GET", "/v1/admin/lessons/1")).status_code == 401
    assert (
        await client.request("GET", "/v1/admin/lessons/1", headers=student_headers)
    ).status_code == 403


async def test_read_lesson(client, admin_headers, draft_course):
    _, lessons, _ = draft_course
    assert (
        await client.get(f"/v1/admin/lessons/{lessons[0]['id']}", headers=admin_headers)
    ).json() == lessons[0]


async def test_read_question_requires_administrator(client, student_headers):
    assert (await client.request("GET", "/v1/admin/questions/1")).status_code == 401
    assert (
        await client.request("GET", "/v1/admin/questions/1", headers=student_headers)
    ).status_code == 403


async def test_read_question(client, admin_headers, draft_course):
    _, _, question = draft_course
    assert (
        await client.get(f"/v1/admin/questions/{question['id']}", headers=admin_headers)
    ).json() == question


async def test_update_course_requires_administrator(client, student_headers):
    assert (await client.request("PUT", "/v1/admin/courses/1")).status_code == 401
    assert (
        await client.request("PUT", "/v1/admin/courses/1", headers=student_headers)
    ).status_code == 403


async def test_update_course_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "PUT",
            "/v1/admin" + f"/courses/{course['id']}",
            headers=admin_headers,
            json={"title": "Changed", "published": False},
        )
    ).status_code == 409


async def test_publish(client, admin_headers, draft_course):
    course, _, _ = draft_course
    response = await client.put(
        f"/v1/admin/courses/{course['id']}",
        headers=admin_headers,
        json={"title": "Published", "published": True},
    )
    assert response.status_code == 200
    assert response.json()["published"] is True
    assert response.json()["title"] == "Published"


async def test_publishing_requires_lessons(client, admin_headers):
    course = (
        await client.post("/v1/admin/courses", headers=admin_headers, json={"title": "Empty"})
    ).json()
    assert (
        await client.put(
            f"/v1/admin/courses/{course['id']}",
            headers=admin_headers,
            json={"title": "Empty", "published": True},
        )
    ).status_code == 409


async def test_update_lesson_requires_administrator(client, student_headers):
    assert (await client.request("PUT", "/v1/admin/lessons/1")).status_code == 401
    assert (
        await client.request("PUT", "/v1/admin/lessons/1", headers=student_headers)
    ).status_code == 403


async def test_update_lesson_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "PUT",
            "/v1/admin" + f"/lessons/{lessons[0]['id']}",
            headers=admin_headers,
            json={"title": "Changed", "content": "x", "position": 1},
        )
    ).status_code == 409


async def test_update_lesson(client, admin_headers, draft_course):
    _, lessons, _ = draft_course
    payload = {
        "title": "Updated",
        "description": "Details",
        "content": "Updated text",
        "position": 2,
        "video_url": "https://example.com/lesson.mp4",
    }
    response = await client.put(
        f"/v1/admin/lessons/{lessons[0]['id']}", headers=admin_headers, json=payload
    )
    assert response.status_code == 200
    assert response.json() == {**lessons[0], **payload}


async def test_update_question_requires_administrator(client, student_headers):
    assert (await client.request("PUT", "/v1/admin/questions/1")).status_code == 401
    assert (
        await client.request("PUT", "/v1/admin/questions/1", headers=student_headers)
    ).status_code == 403


async def test_update_question_enrolled_content_is_frozen(client, admin_headers, enrolled_course):
    course, lessons, question = enrolled_course
    assert (
        await client.request(
            "PUT",
            "/v1/admin" + f"/questions/{question['id']}",
            headers=admin_headers,
            json={"prompt": "x", "options": ["A", "B"], "correct_option": 1, "position": 1},
        )
    ).status_code == 409


async def test_update_question(client, admin_headers, draft_course, question_payload):
    _, _, question = draft_course
    payload = {**question_payload, "correct_option": 1}
    response = await client.put(
        f"/v1/admin/questions/{question['id']}", headers=admin_headers, json=payload
    )
    assert response.status_code == 200
    assert response.json() == {**question, **payload}
