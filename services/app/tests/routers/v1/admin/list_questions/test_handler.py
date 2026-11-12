import pytest

pytestmark = pytest.mark.anyio


async def test_list(client, admin_headers, draft_course):
    _, lessons, question = draft_course
    assert (
        await client.get(f"/v1/admin/lessons/{lessons[0]['id']}/questions", headers=admin_headers)
    ).json()["items"] == [question]
