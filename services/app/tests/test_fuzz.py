"""Exercise the HTTP boundary and filesystem with generated, isolated requests."""

import json
import string
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import pytest
import schemathesis
from fastapi.testclient import TestClient
from hypothesis import example, given
from hypothesis import strategies as st
from schemathesis.checks import (
    content_type_conformance,
    not_a_server_error,
    response_schema_conformance,
    status_code_conformance,
)
from schemathesis.generation import GenerationMode

from app.main import create_app

pytestmark = pytest.mark.fuzz

# Include several Cyrillic alphabets, without deriving expectations from validators.
UPPERCASE = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯІЇЄҐЂЈЉЊЋЏ"
NAMES = st.builds(
    lambda initial, rest: initial + rest,
    st.sampled_from(UPPERCASE),
    st.text(alphabet=UPPERCASE + UPPERCASE.lower(), max_size=50),
)
REASONS = ["нет доступа к сети", "не работает телефон", "не приходят письма"]
FIELDS = ["last_name", "first_name", "birth_date", "phone", "email", "reasons", "detected_at"]
JSON_VALUES = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=100)
    | st.sampled_from(["\ud800", "\udfff"]),
    lambda children: (
        st.lists(children, max_size=8) | st.dictionaries(st.text(max_size=30), children, max_size=8)
    ),
    max_leaves=20,
)
VALID_APPEALS = st.fixed_dictionaries(
    {
        "last_name": NAMES,
        "first_name": NAMES,
        "birth_date": st.dates(min_value=date(1900, 1, 1), max_value=date(2020, 12, 31)).map(
            date.isoformat
        ),
        "phone": st.builds(
            lambda initial, rest: "+" + initial + rest,
            st.sampled_from("123456789"),
            st.text(alphabet=string.digits, min_size=7, max_size=14),
        ),
        "email": st.builds(
            lambda local, domain: f"{local}@{domain}",
            st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=30),
            st.sampled_from(["example.com", "EXAMPLE.COM", "example.org"]),
        ),
        "reasons": st.lists(st.sampled_from(REASONS), min_size=1, max_size=3, unique=True),
        "detected_at": st.datetimes(
            min_value=datetime(2021, 1, 1),
            max_value=datetime(2025, 12, 31),
            timezones=st.sampled_from(
                [UTC, timezone(timedelta(hours=3)), timezone(timedelta(hours=-5, minutes=-30))]
            ),
        ).map(datetime.isoformat),
    }
)
SCHEMA = schemathesis.openapi.from_dict(create_app().openapi())
OPERATION = SCHEMA["/appeals"]["POST"]
RESPONSE_CHECKS = [
    not_a_server_error,
    status_code_conformance,
    content_type_conformance,
    response_schema_conformance,
]


@contextmanager
def isolated_client():
    # Pytest function fixtures are shared across Hypothesis examples. Instead,
    # allocate and clean up the application and directory for every example.
    with TemporaryDirectory(prefix="appeals-fuzz-") as directory:
        data_dir = Path(directory) / "appeals"
        with TestClient(create_app(data_dir=data_dir)) as client:
            yield client, data_dir


def assert_persistence(response, data_dir):
    files = list(data_dir.iterdir()) if data_dir.exists() else []
    if response.status_code == 201:
        body = response.json()
        assert UUID(body["id"]).version == 4
        assert files == [data_dir / f"{body['id']}.json"]
        assert json.loads(files[0].read_text(encoding="utf-8")) == body
    else:
        assert files == []
        assert "detail" in response.json()


def post_json(client, body):
    # Escaped surrogates must reach the server instead of failing in HTTPX's
    # UTF-8 encoder before a request is sent.
    return client.post(
        "/appeals",
        content=json.dumps(body, ensure_ascii=True, allow_nan=False),
        headers={"Content-Type": "application/json"},
    )


@given(payload=VALID_APPEALS)
def test_valid_appeals_round_trip(payload):
    with isolated_client() as (client, data_dir):
        response = client.post("/appeals", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert set(body) == {*FIELDS, "id"}
        for field in ["last_name", "first_name", "birth_date", "phone", "reasons"]:
            assert body[field] == payload[field]
        assert body["email"] == payload["email"].lower()
        assert datetime.fromisoformat(body["detected_at"]) == datetime.fromisoformat(
            payload["detected_at"]
        )
        OPERATION.Case(body=payload).validate_response(response, checks=RESPONSE_CHECKS)
        assert_persistence(response, data_dir)


@given(payload=VALID_APPEALS, field=st.sampled_from(FIELDS), value=JSON_VALUES)
def test_mutated_fields_never_crash_or_save_rejected_input(payload, field, value):
    payload = {**payload, field: value}
    with isolated_client() as (client, data_dir):
        response = post_json(client, payload)
        assert response.status_code in (201, 422)
        OPERATION.Case(body=payload).validate_response(response, checks=RESPONSE_CHECKS)
        assert_persistence(response, data_dir)


@pytest.mark.parametrize("field", ["last_name", "first_name"])
@given(
    payload=VALID_APPEALS, invalid_char=st.sampled_from("aZ09 -_'\n\x00🙂"), position=st.integers()
)
def test_non_cyrillic_characters_are_rejected(field, payload, invalid_char, position):
    name = payload[field]
    index = position % (len(name) + 1)
    payload = {**payload, field: name[:index] + invalid_char + name[index:]}
    with isolated_client() as (client, data_dir):
        response = client.post("/appeals", json=payload)
        assert response.status_code == 422
        assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
        assert_persistence(response, data_dir)


@given(body=JSON_VALUES)
def test_arbitrary_json_bodies_never_crash(body):
    with isolated_client() as (client, data_dir):
        response = post_json(client, body)
        assert response.status_code in (201, 422)
        assert_persistence(response, data_dir)


@given(body=st.binary(max_size=2048))
@example(body=b'{"first_name":"\\ud800"}')
@example(body=b'{"first_name":NaN}')
def test_arbitrary_request_bytes_never_crash(body):
    with isolated_client() as (client, data_dir):
        response = client.post(
            "/appeals", content=body, headers={"Content-Type": "application/json"}
        )
        assert response.status_code in (201, 400, 422)
        assert_persistence(response, data_dir)


@pytest.mark.parametrize("mode", list(GenerationMode))
@given(data=st.data())
def test_openapi_generated_requests(mode, data):
    case = data.draw(OPERATION.as_strategy(generation_mode=mode), label="OpenAPI request")
    with isolated_client() as (client, data_dir):
        response = case.call(app=client.app)
        if mode == GenerationMode.NEGATIVE:
            # Negative generation also emits undecodable byte payloads.
            assert response.status_code in (400, 422)
        else:
            # The schema cannot express the custom Cyrillic and past-date rules.
            # Domain-valid acceptance is covered by test_valid_appeals_round_trip.
            assert response.status_code in (201, 422)
        case.validate_response(response, checks=RESPONSE_CHECKS)
        assert_persistence(response, data_dir)
