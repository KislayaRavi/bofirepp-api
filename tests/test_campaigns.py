"""Tests for the /campaigns endpoints (file-system backed, fully isolated)."""
import pytest
from tests.conftest import CAMPAIGN_PAYLOAD, DOMAIN_PAYLOAD, EXPERIMENT_ROWS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_campaign(client, payload=None):
    return client.post("/campaigns", json=payload or CAMPAIGN_PAYLOAD).json()


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_campaign_returns_201(client):
    resp = client.post("/campaigns", json=CAMPAIGN_PAYLOAD)
    assert resp.status_code == 201


def test_create_campaign_response_shape(client):
    body = _create_campaign(client)
    assert "id" in body
    assert body["name"] == CAMPAIGN_PAYLOAD["name"]
    assert body["context"] == CAMPAIGN_PAYLOAD["context"]
    assert body["proposals"] == {}
    assert body["n_experiments"] == 0


def test_create_campaign_without_strategy(client):
    payload = {k: v for k, v in CAMPAIGN_PAYLOAD.items() if k != "strategy"}
    body = _create_campaign(client, payload)
    assert body["strategy"] is None


def test_create_campaign_without_context(client):
    payload = {k: v for k, v in CAMPAIGN_PAYLOAD.items() if k != "context"}
    body = _create_campaign(client, payload)
    assert body["context"] is None


def test_create_campaign_missing_name_returns_422(client):
    payload = {k: v for k, v in CAMPAIGN_PAYLOAD.items() if k != "name"}
    resp = client.post("/campaigns", json=payload)
    assert resp.status_code == 422


def test_create_campaign_missing_domain_returns_422(client):
    payload = {k: v for k, v in CAMPAIGN_PAYLOAD.items() if k != "domain"}
    resp = client.post("/campaigns", json=payload)
    assert resp.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_campaigns_empty(client):
    resp = client.get("/campaigns")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_campaigns_returns_summaries(client):
    _create_campaign(client)
    _create_campaign(client, {**CAMPAIGN_PAYLOAD, "name": "Second"})
    summaries = client.get("/campaigns").json()
    assert len(summaries) == 2
    for s in summaries:
        assert "id" in s
        assert "n_proposals" in s
        assert "n_experiments" in s
        assert "has_strategy" in s


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_campaign_by_id(client):
    created = _create_campaign(client)
    fetched = client.get(f"/campaigns/{created['id']}").json()
    assert fetched["id"] == created["id"]


def test_get_nonexistent_campaign_returns_404(client):
    resp = client.get("/campaigns/does-not-exist")
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_campaign_returns_204(client):
    created = _create_campaign(client)
    resp = client.delete(f"/campaigns/{created['id']}")
    assert resp.status_code == 204


def test_delete_campaign_removes_it(client):
    created = _create_campaign(client)
    client.delete(f"/campaigns/{created['id']}")
    resp = client.get(f"/campaigns/{created['id']}")
    assert resp.status_code == 404


def test_delete_nonexistent_campaign_returns_404(client):
    resp = client.delete("/campaigns/does-not-exist")
    assert resp.status_code == 404


# ── Strategy ──────────────────────────────────────────────────────────────────

def test_set_strategy_returns_200(client):
    created = _create_campaign(client, {k: v for k, v in CAMPAIGN_PAYLOAD.items() if k != "strategy"})
    resp = client.patch(
        f"/campaigns/{created['id']}/strategy",
        json={"strategy": "random", "n_candidates": 4},
    )
    assert resp.status_code == 200


def test_set_strategy_persists(client):
    created = _create_campaign(client)
    client.patch(
        f"/campaigns/{created['id']}/strategy",
        json={"strategy": "sobo", "n_candidates": 2},
    )
    fetched = client.get(f"/campaigns/{created['id']}").json()
    assert fetched["strategy"]["strategy"] == "sobo"
    assert fetched["strategy"]["n_candidates"] == 2


def test_set_strategy_nonexistent_campaign_returns_404(client):
    resp = client.patch(
        "/campaigns/no-such/strategy",
        json={"strategy": "random", "n_candidates": 1},
    )
    assert resp.status_code == 404


def test_set_invalid_strategy_type_returns_422(client):
    created = _create_campaign(client)
    resp = client.patch(
        f"/campaigns/{created['id']}/strategy",
        json={"strategy": "magic", "n_candidates": 1},
    )
    assert resp.status_code == 422


# ── Context ───────────────────────────────────────────────────────────────────

def test_set_context_returns_200(client):
    created = _create_campaign(client)
    resp = client.patch(
        f"/campaigns/{created['id']}/context",
        json={"context": "New context description."},
    )
    assert resp.status_code == 200


def test_set_context_persists(client):
    created = _create_campaign(client)
    new_context = "Updated optimization context."
    client.patch(f"/campaigns/{created['id']}/context", json={"context": new_context})
    fetched = client.get(f"/campaigns/{created['id']}").json()
    assert fetched["context"] == new_context


def test_set_context_nonexistent_campaign_returns_404(client):
    resp = client.patch("/campaigns/no-such/context", json={"context": "x"})
    assert resp.status_code == 404


# ── Experiments ───────────────────────────────────────────────────────────────

def test_add_experiments_returns_201(client):
    created = _create_campaign(client)
    resp = client.post(
        f"/campaigns/{created['id']}/experiments",
        json={"data": EXPERIMENT_ROWS},
    )
    assert resp.status_code == 201


def test_add_experiments_increments_count(client):
    created = _create_campaign(client)
    url = f"/campaigns/{created['id']}/experiments"
    client.post(url, json={"data": EXPERIMENT_ROWS[:2]})
    body = client.post(url, json={"data": EXPERIMENT_ROWS[2:]}).json()
    assert body["n_experiments"] == len(EXPERIMENT_ROWS)


def test_add_experiments_missing_key_returns_422(client):
    created = _create_campaign(client)
    bad_row = {"x1": 0.5, "material": "A"}  # missing x2 and yield
    resp = client.post(
        f"/campaigns/{created['id']}/experiments",
        json={"data": [bad_row]},
    )
    assert resp.status_code == 422


def test_list_campaign_experiments(client):
    created = _create_campaign(client)
    client.post(
        f"/campaigns/{created['id']}/experiments",
        json={"data": EXPERIMENT_ROWS},
    )
    rows = client.get(f"/campaigns/{created['id']}/experiments").json()
    assert len(rows) == len(EXPERIMENT_ROWS)


def test_clear_campaign_experiments(client):
    created = _create_campaign(client)
    url = f"/campaigns/{created['id']}/experiments"
    client.post(url, json={"data": EXPERIMENT_ROWS})
    resp = client.delete(url)
    assert resp.status_code == 204
    assert client.get(url).json() == []


# ── Proposals ─────────────────────────────────────────────────────────────────

def test_generate_initial_proposal_returns_201(client):
    created = _create_campaign(client)
    resp = client.post(f"/campaigns/{created['id']}/proposals/generate", json={})
    assert resp.status_code == 201


def test_generate_initial_proposal_key(client):
    created = _create_campaign(client)
    body = client.post(
        f"/campaigns/{created['id']}/proposals/generate", json={}
    ).json()
    assert "initial_proposal" in body["proposals"]


def test_generate_proposal_candidate_count(client):
    created = _create_campaign(client)
    client.patch(
        f"/campaigns/{created['id']}/strategy",
        json={"strategy": "random", "n_candidates": 4},
    )
    body = client.post(
        f"/campaigns/{created['id']}/proposals/generate", json={}
    ).json()
    assert len(body["proposals"]["initial_proposal"]) == 4


def test_generate_proposal_respects_override_n_candidates(client):
    created = _create_campaign(client)
    body = client.post(
        f"/campaigns/{created['id']}/proposals/generate",
        json={"n_candidates": 7},
    ).json()
    assert len(body["proposals"]["initial_proposal"]) == 7


def test_proposal_keys_are_sequential(client):
    created = _create_campaign(client)
    cid = created["id"]
    client.post(f"/campaigns/{cid}/experiments", json={"data": EXPERIMENT_ROWS})
    client.post(f"/campaigns/{cid}/proposals/generate", json={})
    client.post(f"/campaigns/{cid}/proposals/generate", json={})
    proposals = client.get(f"/campaigns/{cid}/proposals").json()
    assert "initial_proposal" in proposals
    assert "proposal1" in proposals


def test_generate_proposal_without_strategy_returns_422(client):
    payload = {k: v for k, v in CAMPAIGN_PAYLOAD.items() if k != "strategy"}
    created = _create_campaign(client, payload)
    resp = client.post(f"/campaigns/{created['id']}/proposals/generate", json={})
    assert resp.status_code == 422


def test_bayesian_proposal_without_experiments_returns_422(client):
    created = _create_campaign(client)
    client.patch(
        f"/campaigns/{created['id']}/strategy",
        json={"strategy": "sobo", "n_candidates": 2},
    )
    resp = client.post(f"/campaigns/{created['id']}/proposals/generate", json={})
    assert resp.status_code == 422


def test_bayesian_proposal_with_experiments_returns_201(client):
    created = _create_campaign(client)
    cid = created["id"]
    client.patch(
        f"/campaigns/{cid}/strategy",
        json={"strategy": "sobo", "n_candidates": 2},
    )
    client.post(f"/campaigns/{cid}/experiments", json={"data": EXPERIMENT_ROWS})
    resp = client.post(f"/campaigns/{cid}/proposals/generate", json={})
    assert resp.status_code == 201


def test_get_proposals_endpoint(client):
    created = _create_campaign(client)
    cid = created["id"]
    client.post(f"/campaigns/{cid}/proposals/generate", json={})
    proposals = client.get(f"/campaigns/{cid}/proposals").json()
    assert isinstance(proposals, dict)
    assert "initial_proposal" in proposals


# ── Strategy serialization ────────────────────────────────────────────────────

def test_serialize_strategy_returns_201(client):
    created = _create_campaign(client)
    resp = client.post(f"/campaigns/{created['id']}/strategy/serialize")
    assert resp.status_code == 201


def test_serialize_strategy_contains_bofire_spec(client):
    created = _create_campaign(client)
    body = client.post(f"/campaigns/{created['id']}/strategy/serialize").json()
    assert "type" in body
    assert "domain" in body


def test_serialize_strategy_without_strategy_returns_422(client):
    payload = {k: v for k, v in CAMPAIGN_PAYLOAD.items() if k != "strategy"}
    created = _create_campaign(client, payload)
    resp = client.post(f"/campaigns/{created['id']}/strategy/serialize")
    assert resp.status_code == 422


def test_get_serialized_strategy_returns_saved_spec(client):
    created = _create_campaign(client)
    cid = created["id"]
    saved = client.post(f"/campaigns/{cid}/strategy/serialize").json()
    fetched = client.get(f"/campaigns/{cid}/strategy/serialize").json()
    assert fetched == saved


def test_get_serialized_strategy_before_serialize_returns_404(client):
    created = _create_campaign(client)
    resp = client.get(f"/campaigns/{created['id']}/strategy/serialize")
    assert resp.status_code == 404


def test_serialize_all_strategy_types(client):
    # sobo and random work with a single-output domain
    for strategy in ["random", "sobo"]:
        c = _create_campaign(client)
        client.patch(
            f"/campaigns/{c['id']}/strategy",
            json={"strategy": strategy, "n_candidates": 1},
        )
        resp = client.post(f"/campaigns/{c['id']}/strategy/serialize")
        assert resp.status_code == 201, f"Failed for strategy '{strategy}': {resp.text}"
        assert "type" in resp.json()

    # mobo and qparego require at least two output features
    multi_output_payload = {
        "name": "Multi-output test campaign",
        "domain": {
            **DOMAIN_PAYLOAD,
            "output_features": [
                {"key": "yield", "type": "continuous", "objective": "maximize"},
                {"key": "purity", "type": "continuous", "objective": "maximize"},
            ],
        },
        "strategy": {"strategy": "random", "n_candidates": 1},
    }
    for strategy in ["mobo", "qparego"]:
        c = _create_campaign(client, multi_output_payload)
        client.patch(
            f"/campaigns/{c['id']}/strategy",
            json={"strategy": strategy, "n_candidates": 1},
        )
        resp = client.post(f"/campaigns/{c['id']}/strategy/serialize")
        assert resp.status_code == 201, f"Failed for strategy '{strategy}': {resp.text}"
        assert "type" in resp.json()
