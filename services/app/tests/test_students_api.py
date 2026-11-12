import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_student_api_end_to_end(student_client, grade_payload):
    response = student_client.post("/students/grades", json=grade_payload)
    assert response.status_code == 201
    assert response.json() == {**grade_payload, "id": 1}
    assert student_client.get("/students/grades").json() == [response.json()]
    student = {k: grade_payload[k] for k in ("last_name", "first_name", "faculty")}
    assert student_client.get("/students", params={"faculty": "АВТФ"}).json() == [student]
    assert student_client.get("/students/courses").json() == ["Теор. Механика"]
    assert student_client.get(
        "/students/low-grades", params={"course": "Теор. Механика"}
    ).json() == [student]
    assert student_client.get("/students/average", params={"faculty": "АВТФ"}).json() == {
        "faculty": "АВТФ",
        "average_grade": 29.0,
    }


def test_unknown_faculty_and_course_return_empty_results(student_client):
    assert student_client.get("/students", params={"faculty": "Unknown"}).json() == []
    assert student_client.get("/students/low-grades", params={"course": "Unknown"}).json() == []
    assert student_client.get("/students/average", params={"faculty": "Unknown"}).json() == {
        "faculty": "Unknown",
        "average_grade": None,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"grade": -1},
        {"grade": 101},
        {"grade": True},
        {"grade": "29"},
        {"grade": 29.5},
        {"last_name": ""},
        {"faculty": "   "},
        {"course": "x" * 201},
        {"extra": "no"},
        {"first_name": "\ud800"},
        {"course": "\x00"},
    ],
)
def test_invalid_grades_are_not_inserted(student_client, grade_payload, changes):
    response = student_client.post(
        "/students/grades",
        content=json.dumps(grade_payload | changes),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert student_client.get("/students/grades").json() == []


@pytest.mark.parametrize(
    "endpoint,field",
    [
        ("/students", "faculty"),
        ("/students/average", "faculty"),
        ("/students/low-grades", "course"),
    ],
)
def test_query_filters_are_required_and_nonempty(student_client, endpoint, field):
    assert student_client.get(endpoint).status_code == 422
    for value in ["", "   ", "x" * 201, "\x00"]:
        assert student_client.get(endpoint, params={field: value}).status_code == 422


def test_database_persists_across_app_instances(tmp_path, grade_payload):
    from app.students.database import upgrade_database

    url = f"sqlite:///{tmp_path / 'persistent.sqlite3'}"
    first = create_app(database_url=url)
    upgrade_database(first.state.student_engine)
    with TestClient(first) as client:
        assert client.post("/students/grades", json=grade_payload).status_code == 201
    with TestClient(create_app(database_url=url)) as client:
        assert client.get("/students/grades").json() == [{**grade_payload, "id": 1}]


def test_missing_schema_returns_safe_service_error_and_keeps_appeals_working(tmp_path, payload):
    app = create_app(data_dir=tmp_path / "appeals", database_url=f"sqlite:///{tmp_path / 'new.db'}")
    with TestClient(app) as client:
        response = client.get("/students/courses")
        assert response.status_code == 503
        assert "migrations" in response.json()["detail"]
        assert str(tmp_path) not in response.text
        assert client.get("/health/live").status_code == 200
        assert client.post("/appeals", json=payload).status_code == 201
