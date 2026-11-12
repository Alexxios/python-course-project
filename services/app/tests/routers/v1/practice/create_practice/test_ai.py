import json

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.models import PracticeQuiz

pytestmark = pytest.mark.anyio


def ai_response(lesson_id):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "questions": [
                                    {
                                        "source_lesson_id": lesson_id,
                                        "prompt": "Which collection is immutable?",
                                        "options": ["list", "tuple"],
                                        "correct_option": 1,
                                    }
                                ]
                            }
                        ),
                    }
                ],
            }
        ],
    }


async def test_ai_generation_uses_only_completed_material(
    client, application, student_headers, learned_course, respx_mock
):
    course, lessons, _ = learned_course
    application.state.settings.quiz_generator = "openai"
    application.state.settings.openai_api_key = SecretStr("test-api-key")
    application.state.settings.openai_model = "configured-model"
    route = respx_mock.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json=ai_response(lessons[0]["id"]))
    )
    response = await client.post(
        "/v1/me/practice-quizzes",
        headers=student_headers,
        json={"course_id": course["id"], "question_count": 1},
    )
    assert response.status_code == 201, response.text
    assert response.json()["source"] == "openai"
    assert "correct_option" not in response.text
    sent = json.loads(route.calls[0].request.content)
    assert sent["store"] is False
    assert sent["text"]["format"]["strict"] is True
    material = json.loads(sent["input"][1]["content"])
    assert [item["lesson_id"] for item in material["lessons"]] == [lessons[0]["id"]]
    assert "password" not in str(material) and "username" not in str(material)
    result = await client.post(
        f"/v1/me/practice-quizzes/{response.json()['id']}/submit",
        headers=student_headers,
        json={"answers": [{"question_id": 1, "option": 1}]},
    )
    assert result.json()["score"] == 100


@pytest.mark.parametrize(
    "failure",
    ["http", "timeout", "refusal", "invalid_json", "unlearned", "invalid_option", "wrong_count"],
)
async def test_ai_failures_never_persist_bad_quizzes(
    client, application, student_headers, learned_course, respx_mock, failure
):
    course, lessons, _ = learned_course
    application.state.settings.quiz_generator = "openai"
    application.state.settings.openai_api_key = SecretStr("test-api-key")
    application.state.settings.openai_model = "configured-model"
    body = ai_response(lessons[0]["id"])
    if failure == "refusal":
        body["output"] = [{"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}]
    elif failure == "invalid_json":
        body["output"][0]["content"][0]["text"] = "invalid"
    elif failure in ("unlearned", "invalid_option", "wrong_count"):
        content = json.loads(body["output"][0]["content"][0]["text"])
        if failure == "unlearned":
            content["questions"][0]["source_lesson_id"] = lessons[1]["id"]
        elif failure == "invalid_option":
            content["questions"][0]["correct_option"] = 5
        else:
            content["questions"] *= 2
        body["output"][0]["content"][0]["text"] = json.dumps(content)
    route = respx_mock.post("https://api.openai.com/v1/responses")
    if failure == "timeout":
        route.mock(side_effect=httpx.ReadTimeout("Timed out"))
    else:
        route.mock(return_value=httpx.Response(429 if failure == "http" else 200, json=body))
    response = await client.post(
        "/v1/me/practice-quizzes",
        headers=student_headers,
        json={"course_id": course["id"], "question_count": 1},
    )
    assert response.status_code == 502
    async with application.state.sessions() as db:
        assert await db.scalar(select(PracticeQuiz.id)) is None


async def test_ai_configuration_is_required(client, application, student_headers, learned_course):
    course, _, _ = learned_course
    application.state.settings.quiz_generator = "openai"
    application.state.settings.openai_api_key = None
    response = await client.post(
        "/v1/me/practice-quizzes", headers=student_headers, json={"course_id": course["id"]}
    )
    assert response.status_code == 503
