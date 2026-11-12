import pytest

pytestmark = pytest.mark.anyio


async def test_delete(client, admin_headers, draft_course):
    _, _, question = draft_course
    url = f"/v1/admin/questions/{question['id']}"
    assert (await client.delete(url, headers=admin_headers)).status_code == 204
    assert (await client.get(url, headers=admin_headers)).status_code == 404
