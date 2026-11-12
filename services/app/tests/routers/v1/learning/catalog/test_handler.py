import pytest

pytestmark = pytest.mark.anyio


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
