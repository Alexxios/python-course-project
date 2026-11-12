import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("value", [0, -1, 2147483648, 9223372036854775808, 10**100])
async def test_identifier_bounds(client, student_headers, value):
    assert (
        await client.get("/v1/me/attempts", headers=student_headers, params={"course_id": value})
    ).status_code == 422
