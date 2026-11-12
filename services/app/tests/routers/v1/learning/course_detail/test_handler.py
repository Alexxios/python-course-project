import pytest

pytestmark = pytest.mark.anyio


async def test_public_description_and_hidden_drafts(client, course_factory):
    public, _, _ = await course_factory()
    hidden, _, _ = await course_factory(published=False)
    assert (await client.get(f"/v1/courses/{public['id']}")).json() == public
    assert (await client.get(f"/v1/courses/{hidden['id']}")).status_code == 404
