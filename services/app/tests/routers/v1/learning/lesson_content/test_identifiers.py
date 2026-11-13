import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("value", [0, -1, 2147483648, 9223372036854775808, 10**100])
async def test_identifier_bounds(client, student_headers, value):
    assert (await client.get(f"/v1/lessons/{value}", headers=student_headers)).status_code == 422
