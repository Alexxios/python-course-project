import pytest


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
def test_unsafe_validation_input_returns_field_errors(client, data_dir, body):
    response = client.post("/appeals", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"
    errors = response.json()["detail"]
    assert errors
    assert all(set(error) == {"loc", "msg", "type"} for error in errors)
    assert not data_dir.exists()


@pytest.mark.parametrize("body", [b"\xff", b"\x00" * 21])
def test_undecodable_request_body_returns_400(client, data_dir, body):
    response = client.post("/appeals", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json() == {"detail": "There was an error parsing the body"}
    assert not data_dir.exists()
