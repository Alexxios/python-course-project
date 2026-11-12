import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("parameters", [{"offset": 9223372036854775808}, {"search": "\x00"}])
async def test_bad_catalog_parameters_are_rejected(client, parameters):
    assert (await client.get("/v1/courses", params=parameters)).status_code == 422
