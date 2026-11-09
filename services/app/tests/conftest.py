import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def payload():
    return {
        "last_name": "Иванов",
        "first_name": "Семён",
        "birth_date": "1990-05-21",
        "phone": "+79991234567",
        "email": "ivanov@example.com",
        "reasons": ["нет доступа к сети"],
        "detected_at": "2025-01-15T10:30:00+03:00",
    }


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "appeals"


@pytest.fixture
def client(data_dir):
    with TestClient(create_app(data_dir=data_dir)) as client:
        yield client
