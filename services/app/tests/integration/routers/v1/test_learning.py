import asyncio

import pytest
import schemathesis
from httpx import ASGITransport, AsyncClient
from hypothesis import given
from hypothesis import strategies as st
from schemathesis.checks import (
    content_type_conformance,
    not_a_server_error,
    response_schema_conformance,
    status_code_conformance,
)
from schemathesis.generation import GenerationMode

from app.main import app

pytestmark = pytest.mark.anyio


SCHEMA = schemathesis.openapi.from_dict(app.openapi())


CHECKS = [
    content_type_conformance,
    not_a_server_error,
    response_schema_conformance,
    status_code_conformance,
]


@pytest.fixture
async def enrolled_course(client, student_headers, course_factory):
    course, lessons, question = await course_factory()
    response = await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    assert response.status_code == 201, response.text
    return (course, lessons, question)


@pytest.fixture
async def finished_course(client, student_headers, learned_course):
    course, lessons, question = learned_course
    response = await client.post(
        f"/v1/lessons/{lessons[1]['id']}/complete", headers=student_headers
    )
    assert response.status_code == 200, response.text
    return (learned_course, response.json())


@pytest.mark.parametrize("parameters", [{"offset": 9223372036854775808}, {"search": "\x00"}])
async def test_bad_catalog_parameters_are_rejected(client, parameters):
    assert (await client.get("/v1/courses", params=parameters)).status_code == 422


async def test_database_error_is_safe(application_factory):
    async with (
        application_factory(migrate=False) as app,
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
    ):
        response = await client.get("/v1/courses")
        assert response.status_code == 503
        assert response.json() == {
            "detail": "Database unavailable; check configuration and migrations"
        }


@pytest.mark.fuzz
@pytest.mark.parametrize("mode", list(GenerationMode))
@given(data=st.data())
def test_catalog_openapi_inputs(application_factory, mode, data):
    case = data.draw(SCHEMA["/v1/courses"]["GET"].as_strategy(generation_mode=mode))
    asyncio.run(check_case(case, application_factory))


async def check_case(case, application_factory):
    async with (
        application_factory() as app,
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
    ):
        request = case.as_transport_kwargs(base_url="http://testserver")
        client.cookies.update(request.pop("cookies", {}))
        response = await client.request(**request)
        case.validate_response(response, checks=CHECKS)
        assert response.status_code in (200, 400, 404, 422)


async def test_search_pagination_and_draft_filter(client, course_factory):
    first, _, _ = await course_factory("Python")
    await course_factory("SQL")
    await course_factory("Secret", published=False)
    result = (await client.get("/v1/courses", params={"limit": 1, "offset": 1})).json()
    assert result["total"] == 2
    assert result["items"][0]["title"] == "SQL"
    assert (await client.get("/v1/courses", params={"search": "python"})).json()["items"] == [first]
    assert (await client.get("/v1/courses", params={"search": "%"})).json()["items"] == []
    assert (await client.get("/v1/courses?limit=101")).status_code == 422
    assert (await client.get("/v1/courses?offset=-1")).status_code == 422


async def test_cannot_skip_lessons_or_bypass_a_test(client, student_headers, enrolled_course):
    _, lessons, _ = enrolled_course
    assert (
        await client.post(f"/v1/lessons/{lessons[1]['id']}/complete", headers=student_headers)
    ).status_code == 403
    assert (
        await client.post(f"/v1/lessons/{lessons[0]['id']}/complete", headers=student_headers)
    ).status_code == 409


async def test_completion_is_idempotent(client, student_headers, learned_course):
    _, lessons, _ = learned_course
    url = f"/v1/lessons/{lessons[1]['id']}/complete"
    finished = (await client.post(url, headers=student_headers)).json()
    assert finished["progress_percent"] == 100 and finished["next_lesson_id"] is None
    assert (await client.post(url, headers=student_headers)).json() == finished


@pytest.mark.fuzz
@pytest.mark.parametrize("mode", list(GenerationMode))
@given(data=st.data())
def test_course_detail_openapi_inputs(application_factory, mode, data):
    case = data.draw(SCHEMA["/v1/courses/{course_id}"]["GET"].as_strategy(generation_mode=mode))
    asyncio.run(check_case(case, application_factory))


async def test_public_description_and_hidden_drafts(client, course_factory):
    public, _, _ = await course_factory()
    hidden, _, _ = await course_factory(published=False)
    assert (await client.get(f"/v1/courses/{public['id']}")).json() == public
    assert (await client.get(f"/v1/courses/{hidden['id']}")).status_code == 404


@pytest.mark.parametrize("value", [0, -1, 2147483648, 9223372036854775808, 10**100])
async def test_course_detail_identifier_bounds(client, student_headers, value):
    assert (await client.get(f"/v1/courses/{value}")).status_code == 422


async def test_outline_marks_locked_lessons_without_content(
    client, student_headers, enrolled_course
):
    course, _, _ = enrolled_course
    result = (
        await client.get(f"/v1/courses/{course['id']}/lessons", headers=student_headers)
    ).json()
    assert [lesson["unlocked"] for lesson in result] == [True, False]
    assert "content" not in str(result)


async def test_enroll_once(client, student_headers, course_factory):
    course, _, _ = await course_factory()
    url = f"/v1/courses/{course['id']}/enroll"
    response = await client.post(url, headers=student_headers)
    assert response.status_code == 201
    assert response.json()["progress_percent"] == 0
    assert (await client.post(url, headers=student_headers)).status_code == 409


async def test_cannot_enroll_in_a_draft(client, student_headers, course_factory):
    course, _, _ = await course_factory(published=False)
    assert (
        await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    ).status_code == 404


async def test_enrollment_and_prerequisites(client, student_headers, course_factory):
    course, lessons, _ = await course_factory()
    assert (
        await client.get(f"/v1/lessons/{lessons[0]['id']}", headers=student_headers)
    ).status_code == 403
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    assert (
        await client.get(f"/v1/lessons/{lessons[1]['id']}", headers=student_headers)
    ).status_code == 403
    response = await client.get(f"/v1/lessons/{lessons[0]['id']}", headers=student_headers)
    assert response.json()["content"] == lessons[0]["content"]
    assert "correct_option" not in response.text


async def test_completed_content_remains_available_and_private(
    client, student_headers, learned_course, account_factory
):
    course, lessons, _ = learned_course
    assert (await client.get(f"/v1/lessons/{lessons[0]['id']}", headers=student_headers)).json()[
        "completed"
    ] is True
    assert (
        await client.get(f"/v1/lessons/{lessons[1]['id']}", headers=student_headers)
    ).status_code == 200
    _, other, _ = await account_factory("other")
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=other)
    assert (await client.get(f"/v1/lessons/{lessons[1]['id']}", headers=other)).status_code == 403


@pytest.mark.parametrize("value", [0, -1, 2147483648, 9223372036854775808, 10**100])
async def test_lesson_content_identifier_bounds(client, student_headers, value):
    assert (await client.get(f"/v1/lessons/{value}", headers=student_headers)).status_code == 422


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


@pytest.mark.parametrize("value", [0, -1, 2147483648, 9223372036854775808, 10**100])
async def test_my_attempts_identifier_bounds(client, student_headers, value):
    assert (
        await client.get("/v1/me/attempts", headers=student_headers, params={"course_id": value})
    ).status_code == 422


async def test_private_course_list(client, student_headers, finished_course, account_factory):
    _, progress = finished_course
    assert (await client.get("/v1/me/courses", headers=student_headers)).json()["items"] == [
        progress
    ]
    _, other, _ = await account_factory("other")
    assert (await client.get("/v1/me/courses", headers=other)).json()["total"] == 0


async def test_private_progress(client, student_headers, learned_course, account_factory):
    course, _, _ = learned_course
    url = f"/v1/me/courses/{course['id']}/progress"
    assert (await client.get(url, headers=student_headers)).json()["progress_percent"] == 50
    _, other, _ = await account_factory("other")
    assert (await client.get(url, headers=other)).status_code == 403


async def test_current_profile(client, account_factory):
    identity, headers, _ = await account_factory()
    response = await client.get("/v1/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == identity
    assert response.json()["username"] == "student"
    assert "password" not in response.text


async def test_grades_retries_and_unlocks_next_lesson(client, student_headers, enrolled_course):
    course, lessons, question = enrolled_course
    url = f"/v1/lessons/{lessons[0]['id']}/attempts"
    payload = {"answers": [{"question_id": question["id"], "option": 1}]}
    wrong = await client.post(url, headers=student_headers, json=payload)
    assert wrong.status_code == 201
    assert wrong.json()["score"] == 0 and wrong.json()["passed"] is False
    assert (
        await client.get(f"/v1/lessons/{lessons[1]['id']}", headers=student_headers)
    ).status_code == 403
    payload["answers"][0]["option"] = 0
    passed = (await client.post(url, headers=student_headers, json=payload)).json()
    assert passed["passed"] is True and passed["score"] == 100
    progress = (
        await client.get(f"/v1/me/courses/{course['id']}/progress", headers=student_headers)
    ).json()
    assert progress["progress_percent"] == 50 and progress["next_lesson_id"] == lessons[1]["id"]


async def test_no_test_lessons_use_completion_endpoint(client, student_headers, course_factory):
    course, lessons, _ = await course_factory(with_test=False)
    await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    assert (
        await client.post(
            f"/v1/lessons/{lessons[0]['id']}/attempts",
            headers=student_headers,
            json={"answers": [{"question_id": 1, "option": 0}]},
        )
    ).status_code == 409
    assert (
        await client.post(f"/v1/lessons/{lessons[0]['id']}/complete", headers=student_headers)
    ).json()["progress_percent"] == 50


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
