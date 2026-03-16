"""
Shared fixtures for the BoFire++ API test suite.

Campaign tests use an in-memory SQLite database so they are fully isolated
from the production database file.  Domain/Experiment/Strategy tests use the
same in-memory store that the router module keeps, which is reset between
test functions by the `reset_domain_store` autouse fixture.
"""
import sys
import os
import pytest

# Make the bofire-api package root importable regardless of how pytest is invoked
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from database import Base, get_db
import db.models  # noqa: F401 — imports all ORM models so Base.metadata knows about them


# ── Test database (in-memory SQLite, shared connection) ───────────────────────

TEST_DATABASE_URL = "sqlite://"  # in-memory

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create all tables once per test session
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── App fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app
    fastapi_app.dependency_overrides[get_db] = override_get_db
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c


# ── Clean campaign table between tests ───────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_campaigns():
    """Wipe the campaigns table before every test so tests are independent."""
    from db.models import Campaign
    db = TestingSessionLocal()
    db.query(Campaign).delete()
    db.commit()
    db.close()
    yield


# ── Reset in-memory domain store between tests ───────────────────────────────

@pytest.fixture(autouse=True)
def reset_domain_store():
    """Clear the in-memory domain dict before every test."""
    from routers.domains import get_domain_store
    store = get_domain_store()
    store.clear()
    yield
    store.clear()


# ── Reusable domain payload ───────────────────────────────────────────────────

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
