"""Tests for GET /health"""


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_health_contains_version(client):
    body = client.get("/health").json()
    assert "version" in body
    assert isinstance(body["version"], str)


def test_health_contains_python_version(client):
    body = client.get("/health").json()
    assert "python_version" in body


def test_health_reports_bofire_availability(client):
    body = client.get("/health").json()
    assert "bofire_available" in body
    assert isinstance(body["bofire_available"], bool)


def test_root_redirects_to_docs(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302, 307, 308)
    assert "/docs" in resp.headers["location"]
