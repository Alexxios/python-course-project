import pytest

pytestmark = pytest.mark.anyio


async def test_read(client, admin_headers, draft_course):
    _, lessons, _ = draft_course
    assert (
        await client.get(f"/v1/admin/lessons/{lessons[0]['id']}", headers=admin_headers)
    ).json() == lessons[0]
