def test_business_routes_and_documentation_are_versioned(client):
    schema = client.get("/v1/openapi.json").json()
    assert schema["info"]["version"] == "1.0.0"
    assert all(path.startswith(("/v1/", "/health/")) for path in schema["paths"])
    assert client.get("/v1/docs").status_code == 200
    assert client.get("/v1/redoc").status_code == 200
    assert client.get("/courses").status_code == 404
    assert client.post("/appeals", json={}).status_code == 404
