from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_missing_schema_fails_readiness_and_returns_safe_errors(tmp_path):
    app = create_app(settings=Settings(database_url=f"sqlite:///{tmp_path / 'missing.db'}"))
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
