import pytest

pytestmark = pytest.mark.anyio


async def test_create(client, admin_headers, draft_course, question_payload):
    _, lessons, _ = draft_course
    payload = {**question_payload, "position": 2}
    response = await client.post(
        f"/v1/admin/lessons/{lessons[0]['id']}/questions", headers=admin_headers, json=payload
    )
    assert response.status_code == 201
    assert all((response.json()[key] == value for key, value in payload.items()))
