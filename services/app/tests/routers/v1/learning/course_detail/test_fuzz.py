import asyncio

import pytest
import schemathesis
from httpx import ASGITransport, AsyncClient
from hypothesis import given
from hypothesis import strategies as st
from schemathesis.checks import (
    content_type_conformance,
    not_a_server_error,
    response_schema_conformance,
    status_code_conformance,
)
from schemathesis.generation import GenerationMode

from app.config import Settings
from app.database import upgrade_database
from app.main import create_app

pytestmark = pytest.mark.fuzz
SCHEMA = schemathesis.openapi.from_dict(
    create_app(settings=Settings(database_url="sqlite://")).openapi()
)
CHECKS = [
    content_type_conformance,
    not_a_server_error,
    response_schema_conformance,
    status_code_conformance,
]


@pytest.mark.parametrize("mode", list(GenerationMode))
@given(data=st.data())
def test_openapi_inputs(mode, data):
    case = data.draw(SCHEMA["/v1/courses/{course_id}"]["GET"].as_strategy(generation_mode=mode))
    asyncio.run(check_case(case))


async def check_case(case):
    app = create_app(settings=Settings(database_url="sqlite://"))
    try:
        await upgrade_database(app.state.engine)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
        ):
            request = case.as_transport_kwargs(base_url="http://testserver")
            client.cookies.update(request.pop("cookies", {}))
            response = await client.request(**request)
            case.validate_response(response, checks=CHECKS)
            assert response.status_code in (200, 400, 404, 422)
    finally:
        await app.state.engine.dispose()
