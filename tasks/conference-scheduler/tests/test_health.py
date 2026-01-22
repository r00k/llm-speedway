"""Health check tests."""


def test_healthz_returns_ok(client):
    """Basic health check endpoint works."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
