import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "body",
    [
        b'{"first_name":"\\ud800"}',
        b'{"\\udfff":1}',
        b'{"email":{"nested":"\\ud800"}}',
        b'{"first_name":NaN}',
        b'{"first_name":Infinity}',
        b'{"first_name":-Infinity}',
        b'{"first_name":1e999}',
        b"NaN",
        b'{"\\ud800":}',
    ],
)
async def test_unsafe_validation_input_returns_field_errors(client, body):
    response = await client.post(
        "/v1/auth/register", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"
    errors = response.json()["detail"]
    assert errors
    assert all(set(error) == {"loc", "msg", "type"} for error in errors)


@pytest.mark.parametrize("body", [b"\xff", b"\x00" * 21])
async def test_undecodable_request_body_returns_400(client, body):
    response = await client.post(
        "/v1/auth/register", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "There was an error parsing the body"}
