import os

import pytest
from fastapi.testclient import TestClient
from hypothesis import settings

from app.main import create_app
from app.students.database import create_database, upgrade_database
from app.students.repository import StudentRepository

settings.register_profile("app", max_examples=50, deadline=None, print_blob=True)
settings.register_profile("fuzz", parent=settings.get_profile("app"), max_examples=1000)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "app"))


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


@pytest.fixture
def student_engine(tmp_path):
    engine = create_database(f"sqlite:///{tmp_path / 'students.sqlite3'}")
    upgrade_database(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def student_repository(student_engine):
    return StudentRepository(student_engine)


@pytest.fixture
def student_client(tmp_path):
    app = create_app(
        data_dir=tmp_path / "appeals", database_url=f"sqlite:///{tmp_path / 'students.sqlite3'}"
    )
    upgrade_database(app.state.student_engine)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def grade_payload():
    return {
        "last_name": "Ли",
        "first_name": "Иван",
        "faculty": "АВТФ",
        "course": "Теор. Механика",
        "grade": 29,
    }
