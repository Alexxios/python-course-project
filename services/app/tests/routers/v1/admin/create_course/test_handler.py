import pytest

pytestmark = pytest.mark.anyio


async def test_create(client, admin_headers):
    response = await client.post(
        "/v1/admin/courses", headers=admin_headers, json={"title": "Draft"}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Draft"
    assert response.json()["published"] is False
