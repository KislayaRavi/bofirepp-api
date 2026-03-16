"""Tests for /domains/{domain_id}/experiments endpoints."""
from tests.conftest import DOMAIN_PAYLOAD, EXPERIMENT_ROWS


def _create_domain(client):
    return client.post("/domains", json=DOMAIN_PAYLOAD).json()


# ── Add experiments ───────────────────────────────────────────────────────────

def test_add_experiments_returns_201(client):
    domain = _create_domain(client)
    resp = client.post(
        f"/domains/{domain['id']}/experiments",
        json={"data": EXPERIMENT_ROWS},
    )
    assert resp.status_code == 201


def test_add_experiments_response_counts(client):
    domain = _create_domain(client)
    body = client.post(
        f"/domains/{domain['id']}/experiments",
        json={"data": EXPERIMENT_ROWS},
    ).json()
    assert body["n_experiments_added"] == len(EXPERIMENT_ROWS)
    assert body["total_experiments"] == len(EXPERIMENT_ROWS)


def test_add_experiments_accumulates(client):
    domain = _create_domain(client)
    url = f"/domains/{domain['id']}/experiments"
    client.post(url, json={"data": EXPERIMENT_ROWS[:2]})
    body = client.post(url, json={"data": EXPERIMENT_ROWS[2:]}).json()
    assert body["total_experiments"] == len(EXPERIMENT_ROWS)


def test_add_experiments_missing_key_returns_422(client):
    domain = _create_domain(client)
    bad_row = {"x1": 0.5, "material": "A"}  # missing x2 and yield
    resp = client.post(
        f"/domains/{domain['id']}/experiments",
        json={"data": [bad_row]},
    )
    assert resp.status_code == 422


def test_add_experiments_unknown_domain_returns_404(client):
    resp = client.post(
        "/domains/no-such-domain/experiments",
        json={"data": EXPERIMENT_ROWS},
    )
    assert resp.status_code == 404


# ── List experiments ──────────────────────────────────────────────────────────

def test_list_experiments_empty(client):
    domain = _create_domain(client)
    resp = client.get(f"/domains/{domain['id']}/experiments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_experiments_returns_all_rows(client):
    domain = _create_domain(client)
    client.post(f"/domains/{domain['id']}/experiments", json={"data": EXPERIMENT_ROWS})
    rows = client.get(f"/domains/{domain['id']}/experiments").json()
    assert len(rows) == len(EXPERIMENT_ROWS)


def test_list_experiments_unknown_domain_returns_404(client):
    resp = client.get("/domains/no-such-domain/experiments")
    assert resp.status_code == 404


# ── Clear experiments ─────────────────────────────────────────────────────────

def test_clear_experiments_returns_204(client):
    domain = _create_domain(client)
    client.post(f"/domains/{domain['id']}/experiments", json={"data": EXPERIMENT_ROWS})
    resp = client.delete(f"/domains/{domain['id']}/experiments")
    assert resp.status_code == 204


def test_clear_experiments_empties_list(client):
    domain = _create_domain(client)
    url = f"/domains/{domain['id']}/experiments"
    client.post(url, json={"data": EXPERIMENT_ROWS})
    client.delete(url)
    assert client.get(url).json() == []


def test_clear_experiments_unknown_domain_returns_404(client):
    resp = client.delete("/domains/no-such-domain/experiments")
    assert resp.status_code == 404
