def test_live(client):
    assert client.get("/health/live").json() == {"status": "ok"}
