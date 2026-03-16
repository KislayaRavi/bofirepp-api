"""Tests for /domains CRUD endpoints."""
import pytest
from tests.conftest import DOMAIN_PAYLOAD


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_domain_returns_201(client):
    resp = client.post("/domains", json=DOMAIN_PAYLOAD)
    assert resp.status_code == 201


def test_create_domain_response_shape(client):
    body = client.post("/domains", json=DOMAIN_PAYLOAD).json()
    assert "id" in body
    assert body["name"] == DOMAIN_PAYLOAD["name"]
    assert len(body["input_features"]) == len(DOMAIN_PAYLOAD["input_features"])
    assert len(body["output_features"]) == len(DOMAIN_PAYLOAD["output_features"])
    assert body["n_experiments"] == 0


def test_create_domain_missing_name_returns_422(client):
    payload = {k: v for k, v in DOMAIN_PAYLOAD.items() if k != "name"}
    resp = client.post("/domains", json=payload)
    assert resp.status_code == 422


def test_create_domain_empty_input_features_returns_422(client):
    payload = {**DOMAIN_PAYLOAD, "input_features": []}
    resp = client.post("/domains", json=payload)
    assert resp.status_code == 422


def test_create_domain_bad_bounds_returns_422(client):
    payload = {
        **DOMAIN_PAYLOAD,
        "input_features": [{"key": "x1", "type": "continuous", "bounds": [1.0]}],
    }
    resp = client.post("/domains", json=payload)
    assert resp.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_domains_empty(client):
    resp = client.get("/domains")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_domains_after_creation(client):
    client.post("/domains", json=DOMAIN_PAYLOAD)
    client.post("/domains", json={**DOMAIN_PAYLOAD, "name": "Second Domain"})
    body = client.get("/domains").json()
    assert len(body) == 2


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_domain_by_id(client):
    created = client.post("/domains", json=DOMAIN_PAYLOAD).json()
    fetched = client.get(f"/domains/{created['id']}").json()
    assert fetched["id"] == created["id"]
    assert fetched["name"] == DOMAIN_PAYLOAD["name"]


def test_get_nonexistent_domain_returns_404(client):
    resp = client.get("/domains/does-not-exist")
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_domain_returns_204(client):
    created = client.post("/domains", json=DOMAIN_PAYLOAD).json()
    resp = client.delete(f"/domains/{created['id']}")
    assert resp.status_code == 204


def test_delete_domain_removes_it(client):
    created = client.post("/domains", json=DOMAIN_PAYLOAD).json()
    client.delete(f"/domains/{created['id']}")
    resp = client.get(f"/domains/{created['id']}")
    assert resp.status_code == 404


def test_delete_nonexistent_domain_returns_404(client):
    resp = client.delete("/domains/does-not-exist")
    assert resp.status_code == 404
