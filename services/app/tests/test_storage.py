import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import create_app


def test_storage_directory_can_be_configured_from_environment(monkeypatch, tmp_path, payload):
    directory = tmp_path / "configured" / "appeals"
    monkeypatch.setenv("APPEALS_DATA_DIR", str(directory))
    with TestClient(create_app()) as client:
        response = client.post("/appeals", json=payload)
    assert response.status_code == 201
    assert json.loads(next(directory.glob("*.json")).read_text()) == response.json()


def test_explicit_directory_overrides_environment(monkeypatch, tmp_path, data_dir, payload):
    ignored_directory = tmp_path / "unused"
    monkeypatch.setenv("APPEALS_DATA_DIR", str(ignored_directory))
    with TestClient(create_app(data_dir=str(data_dir))) as client:
        assert client.post("/appeals", json=payload).status_code == 201
    assert len(list(data_dir.glob("*.json"))) == 1
    assert not ignored_directory.exists()


def test_default_directory_is_relative_to_working_directory(monkeypatch, tmp_path, payload):
    monkeypatch.delenv("APPEALS_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    with TestClient(create_app()) as client:
        assert client.post("/appeals", json=payload).status_code == 201
    assert len(list((tmp_path / "data" / "appeals").glob("*.json"))) == 1


def test_unusable_storage_returns_503(client, payload, data_dir):
    data_dir.write_text("This is a file, not a directory")
    response = client.post("/appeals", json=payload)
    assert response.status_code == 503
    assert response.json() == {"detail": "The appeal could not be saved; please try again later"}
    assert data_dir.read_text() == "This is a file, not a directory"


@pytest.mark.parametrize("stage", ["create", "flush", "rename"])
def test_failed_writes_leave_no_partial_files_and_can_be_retried(
    client, payload, data_dir, monkeypatch, stage
):
    first = client.post("/appeals", json=payload)
    assert first.status_code == 201
    original_files = {file.name: file.read_bytes() for file in data_dir.iterdir()}

    def fail(*args, **kwargs):
        raise OSError("Simulated storage failure")

    with monkeypatch.context() as patch:
        if stage == "create":
            patch.setattr(storage, "NamedTemporaryFile", fail)
        elif stage == "flush":
            patch.setattr(storage.os, "fsync", fail)
        else:
            patch.setattr(Path, "replace", fail)
        response = client.post("/appeals", json=payload)

    assert response.status_code == 503
    assert {file.name: file.read_bytes() for file in data_dir.iterdir()} == original_files
    assert client.post("/appeals", json=payload).status_code == 201
    assert len(list(data_dir.iterdir())) == 2
