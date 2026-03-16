"""
Shared fixtures for the BoFire++ API test suite.

Campaign tests use a temporary directory on disk so they are fully isolated
from the production campaign folder.  Domain/Experiment/Strategy tests use the
same in-memory store that the router module keeps, which is reset between test
functions by the `reset_domain_store` autouse fixture.
"""
import shutil
import sys
import os
import tempfile
from pathlib import Path

import pytest

# Make the bofire-api package root importable regardless of how pytest is invoked
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from storage import CampaignStore, get_campaign_store


# ── Temporary campaign storage (one dir for the whole test session) ───────────

_tmp_dir = tempfile.mkdtemp(prefix="bofire_test_campaigns_")


def _override_get_campaign_store() -> CampaignStore:
    return CampaignStore(Path(_tmp_dir))


# ── App & client fixtures ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app
    fastapi_app.dependency_overrides[get_campaign_store] = _override_get_campaign_store
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c


# ── Clean campaign folder between tests ───────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_campaigns():
    """Wipe all campaign sub-folders before every test so tests are independent."""
    for item in Path(_tmp_dir).iterdir():
        if item.is_dir():
            shutil.rmtree(item)
    yield
    for item in Path(_tmp_dir).iterdir():
        if item.is_dir():
            shutil.rmtree(item)


# ── Reset in-memory domain store between tests ───────────────────────────────

@pytest.fixture(autouse=True)
def reset_domain_store():
    """Clear the in-memory domain dict before every test."""
    from routers.domains import get_domain_store
    store = get_domain_store()
    store.clear()
    yield
    store.clear()


# ── Reusable payloads ─────────────────────────────────────────────────────────

DOMAIN_PAYLOAD = {
    "name": "Test Domain",
    "input_features": [
        {"key": "x1", "type": "continuous", "bounds": [0.0, 1.0]},
        {"key": "x2", "type": "continuous", "bounds": [0.0, 1.0]},
        {"key": "material", "type": "categorical", "categories": ["A", "B", "C"]},
    ],
    "output_features": [
        {"key": "yield", "type": "continuous", "objective": "maximize"},
    ],
}

EXPERIMENT_ROWS = [
    {"x1": 0.1, "x2": 0.2, "material": "A", "yield": 0.55},
    {"x1": 0.5, "x2": 0.5, "material": "B", "yield": 0.70},
    {"x1": 0.8, "x2": 0.9, "material": "C", "yield": 0.82},
    {"x1": 0.3, "x2": 0.7, "material": "A", "yield": 0.65},
]

CAMPAIGN_PAYLOAD = {
    "name": "Test Campaign",
    "domain": DOMAIN_PAYLOAD,
    "strategy": {"strategy": "random", "n_candidates": 3},
    "context": "Maximise yield in a test optimization run.",
}
