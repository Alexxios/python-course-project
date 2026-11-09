import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from itertools import combinations
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import AppealCreate, AppealReason, StoredAppeal

REASONS = [reason.value for reason in AppealReason]
FIELDS = [
    "last_name",
    "first_name",
    "birth_date",
    "phone",
    "email",
    "reasons",
    "detected_at",
]


@pytest.mark.parametrize(
    "reasons", [list(group) for count in range(1, 4) for group in combinations(REASONS, count)]
)
def test_create_appeal_saves_all_fields(client, payload, data_dir, reasons):
    payload["reasons"] = reasons

    response = client.post("/appeals", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"]).version == 4
    assert body == {**payload, "id": body["id"]}
    saved_file = data_dir / f"{body['id']}.json"
    assert list(data_dir.iterdir()) == [saved_file]
    assert json.loads(saved_file.read_text(encoding="utf-8")) == body
    assert "Семён" in saved_file.read_text(encoding="utf-8")
    assert StoredAppeal.model_validate_json(saved_file.read_text()).id == UUID(body["id"])


@pytest.mark.parametrize("field", ["first_name", "last_name"])
@pytest.mark.parametrize("name", ["Ёлкин", "Ё", "Іван", "СЕМЁН"])
def test_cyrillic_names_are_accepted(client, payload, field, name):
    payload[field] = name
    response = client.post("/appeals", json=payload)
    assert response.status_code == 201
    assert response.json()[field] == name


@pytest.mark.parametrize("field", ["first_name", "last_name"])
@pytest.mark.parametrize(
    "name",
    [
        "",
        "иванов",
        "Ivan",
        "Ивaн",
        "Иван1",
        "Иван-Иван",
        "Иван Иван",
        " Иван",
        "Иван\n",
        "Иван🙂",
        123,
    ],
)
def test_invalid_names_are_rejected(client, payload, data_dir, field, name):
    payload[field] = name
    response = client.post("/appeals", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    assert not data_dir.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phone", "79991234567"),
        ("phone", "+7 999 123-45-67"),
        ("phone", "+09991234567"),
        ("phone", "+1234567"),
        ("phone", "+1234567890123456"),
        ("phone", "+79991234567\n"),
        ("phone", "+٧٩٩٩١٢٣٤٥٦٧"),
        ("phone", 79991234567),
        ("email", "not-an-email"),
        ("email", "user@"),
        ("email", "user@example"),
        ("email", "user name@example.com"),
        ("birth_date", "2025-02-29"),
        ("birth_date", "2000-13-01"),
        ("birth_date", "21.05.1990"),
        ("birth_date", "1990-05-21T00:00:00"),
        ("birth_date", "0"),
        ("birth_date", 0),
        ("reasons", []),
        ("reasons", "нет доступа к сети"),
        ("reasons", ["другая причина"]),
        ("reasons", ["нет доступа к сети", "другая причина"]),
        ("reasons", [1]),
        ("detected_at", "not-a-datetime"),
        ("detected_at", "2025-02-29T10:30:00Z"),
        ("detected_at", "2025-01-15T25:30:00Z"),
        ("detected_at", "2025-01-15"),
        ("detected_at", "2025-01-15T10:30:00"),
        ("detected_at", "0"),
        ("detected_at", 0),
    ],
)
def test_invalid_attributes_are_rejected(client, payload, data_dir, field, value):
    payload[field] = value
    response = client.post("/appeals", json=payload)
    assert response.status_code == 422
    assert any(error["loc"][:2] == ["body", field] for error in response.json()["detail"])
    assert not data_dir.exists()


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("missing", [True, False], ids=["missing", "null"])
def test_every_attribute_is_required(client, payload, data_dir, field, missing):
    if missing:
        del payload[field]
    else:
        payload[field] = None
    response = client.post("/appeals", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    assert not data_dir.exists()


@pytest.mark.parametrize("field", ["birth_date", "detected_at"])
def test_future_dates_are_rejected(client, payload, data_dir, field):
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    payload[field] = tomorrow.date().isoformat() if field == "birth_date" else tomorrow.isoformat()
    response = client.post("/appeals", json=payload)
    assert response.status_code == 422
    assert not data_dir.exists()


@pytest.mark.parametrize("phone", ["+12345678", "+123456789012345"])
def test_phone_length_boundaries(client, payload, phone):
    payload["phone"] = phone
    assert client.post("/appeals", json=payload).status_code == 201


def test_leap_day_and_utc_datetime(client, payload):
    payload["birth_date"] = "2000-02-29"
    payload["detected_at"] = "2025-01-15T07:30:00Z"
    assert client.post("/appeals", json=payload).status_code == 201


def test_today_is_a_valid_birth_date(payload):
    payload["birth_date"] = datetime.now(UTC).date().isoformat()
    assert AppealCreate.model_validate(payload).birth_date.isoformat() == payload["birth_date"]


def test_email_is_normalized_in_response_and_storage(client, payload, data_dir):
    payload["email"] = "ivanov@EXAMPLE.COM"
    response = client.post("/appeals", json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == "ivanov@example.com"
    saved = json.loads(next(data_dir.glob("*.json")).read_text())
    assert saved == response.json()


def test_unknown_fields_are_rejected(client, payload, data_dir):
    response = client.post("/appeals", json={**payload, "id": "../../other-file"})
    assert response.status_code == 422
    assert not data_dir.exists()


def test_malformed_json_is_rejected(client, data_dir):
    response = client.post("/appeals", content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert not data_dir.exists()


def test_repeated_submissions_survive_a_restart(payload, data_dir):
    with TestClient(create_app(data_dir=data_dir)) as client:
        first = client.post("/appeals", json=payload)
    with TestClient(create_app(data_dir=data_dir)) as client:
        second = client.post("/appeals", json=payload)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert len(list(data_dir.iterdir())) == 2
    for response in (first, second):
        saved = data_dir / f"{response.json()['id']}.json"
        assert json.loads(saved.read_text()) == response.json()


def test_concurrent_submissions_do_not_overwrite_each_other(client, payload, data_dir):
    submissions = [{**payload, "email": f"subscriber{index}@example.com"} for index in range(8)]

    def submit(body):
        return client.post("/appeals", json=body)

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(submit, submissions))

    assert all(response.status_code == 201 for response in responses)
    assert len({response.json()["id"] for response in responses}) == len(submissions)
    files = list(data_dir.iterdir())
    assert len(files) == len(submissions)
    assert {json.loads(file.read_text())["email"] for file in files} == {
        body["email"] for body in submissions
    }


def test_openapi_describes_validation_and_success(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/appeals"]["post"]
    assert {"201", "422", "503"} <= operation["responses"].keys()
    model = schema["components"]["schemas"]["AppealCreate"]
    assert set(model["required"]) == set(FIELDS)
    assert model["properties"]["reasons"]["minItems"] == 1
    assert schema["components"]["schemas"]["AppealReason"]["enum"] == REASONS
