import asyncio

import httpx
import pytest
from pydantic import SecretStr

pytestmark = pytest.mark.anyio


async def test_waiting_for_ai_does_not_block_other_requests(
    client, application, student_headers, learned_course, respx_mock
):
    course, _, _ = learned_course
    application.state.settings.quiz_generator = "openai"
    application.state.settings.openai_api_key = SecretStr("test-api-key")
    application.state.settings.openai_model = "configured-model"
    started = asyncio.Event()
    release = asyncio.Event()

    async def provider_response(request):
        started.set()
        await release.wait()
        return httpx.Response(503)

    respx_mock.post("https://api.openai.com/v1/responses").mock(side_effect=provider_response)
    generation = asyncio.create_task(
        client.post(
            "/v1/me/practice-quizzes", headers=student_headers, json={"course_id": course["id"]}
        )
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=3)
        assert not generation.done()
        response = await asyncio.wait_for(client.get("/health/live"), timeout=1)
        assert response.status_code == 200
    finally:
        release.set()
        response = await generation
    assert response.status_code == 502
