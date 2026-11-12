import pytest

pytestmark = pytest.mark.anyio


async def test_update(client, admin_headers, draft_course, question_payload):
    _, _, question = draft_course
    payload = {**question_payload, "correct_option": 1}
    response = await client.put(
        f"/v1/admin/questions/{question['id']}", headers=admin_headers, json=payload
    )
    assert response.status_code == 200
    assert response.json() == {**question, **payload}
