import pytest

pytestmark = pytest.mark.anyio


async def test_read(client, admin_headers, draft_course):
    _, _, question = draft_course
    assert (
        await client.get(f"/v1/admin/questions/{question['id']}", headers=admin_headers)
    ).json() == question
