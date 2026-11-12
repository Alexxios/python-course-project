import pytest


@pytest.fixture
def registration(password):
    return {"username": "student", "first_name": "Иван", "last_name": "Ли", "password": password}
