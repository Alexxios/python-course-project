from fastapi.testclient import TestClient


def test_health_tracks_lifespan_and_database(application):
    assert application.state.ready is False
    with TestClient(application) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").json() == {"status": "ready"}
        application.state.ready = False
        assert client.get("/health/ready").status_code == 503
    assert application.state.ready is False
