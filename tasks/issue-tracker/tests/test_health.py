"""Health check tests."""


def test_healthz_returns_200(client):
    """Health endpoint should return 200."""
    resp = client.get("/healthz")
    assert resp.status_code == 200


def test_healthz_returns_json(client):
    """Health endpoint should return JSON."""
    resp = client.get("/healthz")
    data = resp.json()
    assert "status" in data or resp.status_code == 200
