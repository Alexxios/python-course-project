from fastapi.testclient import TestClient

from app.main import create_app


def test_health_tracks_lifespan(data_dir):
    app = create_app(data_dir=data_dir)
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").json() == {"status": "ready"}
        app.state.ready = False
        assert client.get("/health/ready").status_code == 503
        assert client.get("/health/live").status_code == 200
    assert app.state.ready is False
    assert not data_dir.exists()


def test_readiness_before_startup(data_dir):
    app = create_app(data_dir=data_dir)
    client = TestClient(app)
    try:
        assert client.get("/health/ready").status_code == 503
    finally:
        client.close()


def test_app_instances_have_independent_lifecycles(tmp_path):
    first = create_app(data_dir=tmp_path / "first")
    second = create_app(data_dir=tmp_path / "second")
    with TestClient(first), TestClient(second):
        first.state.ready = False
        assert second.state.ready is True
    assert first.state.ready is second.state.ready is False
