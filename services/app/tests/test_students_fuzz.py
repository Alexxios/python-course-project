"""Generated student requests use the same Hypothesis and Schemathesis stack."""

import pytest
import schemathesis
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from schemathesis.checks import (
    content_type_conformance,
    not_a_server_error,
    response_schema_conformance,
    status_code_conformance,
)
from schemathesis.generation import GenerationMode

from app.main import create_app
from app.students.database import upgrade_database

pytestmark = pytest.mark.fuzz

OPERATION = schemathesis.openapi.from_dict(create_app().openapi())["/students/grades"]["POST"]


@pytest.mark.parametrize("mode", list(GenerationMode))
@given(data=st.data())
def test_student_openapi_requests(mode, data):
    case = data.draw(OPERATION.as_strategy(generation_mode=mode))
    app = create_app(database_url="sqlite://")
    upgrade_database(app.state.student_engine)
    with TestClient(app) as client:
        response = case.call(app=app)
        assert response.status_code in (
            (400, 422) if mode == GenerationMode.NEGATIVE else (201, 422)
        )
        # OpenAPI cannot express strict Python integers (17.0 is a JSON Schema integer)
        # or all text rules. Validate the response contract; acceptance is tested below.
        case.validate_response(
            response,
            checks=[
                not_a_server_error,
                status_code_conformance,
                content_type_conformance,
                response_schema_conformance,
            ],
        )
        records = client.get("/students/grades").json()
        assert records == ([response.json()] if response.status_code == 201 else [])


@given(grades=st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=20))
def test_averages_and_low_grade_queries(grades):
    app = create_app(database_url="sqlite://")
    upgrade_database(app.state.student_engine)
    with TestClient(app) as client:
        for grade in grades:
            response = client.post(
                "/students/grades",
                json={
                    "last_name": "Ли",
                    "first_name": "Иван",
                    "faculty": "АВТФ",
                    "course": "Физика",
                    "grade": grade,
                },
            )
            assert response.status_code == 201
        average = client.get("/students/average", params={"faculty": "АВТФ"}).json()
        assert average["average_grade"] == pytest.approx(sum(grades) / len(grades))
        students = client.get("/students/low-grades", params={"course": "Физика"}).json()
        assert len(students) == int(any(grade < 30 for grade in grades))
