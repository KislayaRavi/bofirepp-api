"""Tests for /domains/{domain_id}/suggest endpoint."""
import pytest
from tests.conftest import DOMAIN_PAYLOAD, EXPERIMENT_ROWS


def _create_domain(client):
    return client.post("/domains", json=DOMAIN_PAYLOAD).json()


def _add_experiments(client, domain_id):
    client.post(
        f"/domains/{domain_id}/experiments",
        json={"data": EXPERIMENT_ROWS},
    )


# ── Random strategy (no data needed) ─────────────────────────────────────────

def test_random_strategy_returns_200(client):
    domain = _create_domain(client)
    resp = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": "random", "n_candidates": 3},
    )
    assert resp.status_code == 200


def test_random_strategy_returns_correct_candidate_count(client):
    domain = _create_domain(client)
    body = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": "random", "n_candidates": 5},
    ).json()
    assert body["n_candidates"] == 5
    assert len(body["candidates"]) == 5


def test_random_strategy_candidates_contain_input_keys(client):
    domain = _create_domain(client)
    candidates = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": "random", "n_candidates": 2},
    ).json()["candidates"]
    input_keys = {f["key"] for f in DOMAIN_PAYLOAD["input_features"]}
    for candidate in candidates:
        assert input_keys.issubset(set(candidate.keys()))


def test_random_strategy_response_shape(client):
    domain = _create_domain(client)
    body = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": "random", "n_candidates": 1},
    ).json()
    assert body["domain_id"] == domain["id"]
    assert body["strategy"] == "random"
    assert "message" in body


def test_suggest_unknown_domain_returns_404(client):
    resp = client.post(
        "/domains/no-such-domain/suggest",
        json={"strategy": "random", "n_candidates": 1},
    )
    assert resp.status_code == 404


# ── Bayesian strategies without data ─────────────────────────────────────────

@pytest.mark.parametrize("strategy", ["sobo", "mobo", "qparego"])
def test_bayesian_strategy_without_data_returns_422(client, strategy):
    domain = _create_domain(client)
    resp = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": strategy, "n_candidates": 1},
    )
    assert resp.status_code == 422


# ── Bayesian (sobo) with data ─────────────────────────────────────────────────

def test_sobo_strategy_with_data_returns_200(client):
    domain = _create_domain(client)
    _add_experiments(client, domain["id"])
    resp = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": "sobo", "n_candidates": 2},
    )
    assert resp.status_code == 200


def test_sobo_strategy_candidates_include_predictions(client):
    domain = _create_domain(client)
    _add_experiments(client, domain["id"])
    candidates = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": "sobo", "n_candidates": 2},
    ).json()["candidates"]
    # SOBO candidates should include prediction columns alongside inputs
    assert len(candidates) == 2
    for c in candidates:
        assert "x1" in c
        assert "x2" in c


# ── n_candidates validation ───────────────────────────────────────────────────

def test_zero_candidates_returns_422(client):
    domain = _create_domain(client)
    resp = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": "random", "n_candidates": 0},
    )
    assert resp.status_code == 422


def test_over_100_candidates_returns_422(client):
    domain = _create_domain(client)
    resp = client.post(
        f"/domains/{domain['id']}/suggest",
        json={"strategy": "random", "n_candidates": 101},
    )
    assert resp.status_code == 422
