from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timezone
import uuid

from models.domain import DomainCreate, DomainResponse

router = APIRouter(prefix="/domains", tags=["Domains"])

# In-memory store (replace with DB in production)
_domains: dict[str, dict] = {}


@router.post(
    "",
    response_model=DomainResponse,
    status_code=201,
    summary="Create optimization domain",
    description=(
        "Define an optimization domain by specifying input features (the design space) "
        "and output features (the objectives to optimize). The domain stores all "
        "experimental data and is the entry point for suggesting new experiments."
    ),
)
def create_domain(payload: DomainCreate) -> DomainResponse:
    domain_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": domain_id,
        "name": payload.name,
        "input_features": [f.model_dump() for f in payload.input_features],
        "output_features": [f.model_dump() for f in payload.output_features],
        "experiments": [],
        "created_at": now,
    }
    _domains[domain_id] = record
    return DomainResponse(
        id=domain_id,
        name=payload.name,
        input_features=payload.input_features,
        output_features=payload.output_features,
        n_experiments=0,
        created_at=now,
    )


@router.get(
    "",
    response_model=List[DomainResponse],
    summary="List all domains",
    description="Return a list of all registered optimization domains.",
)
def list_domains() -> List[DomainResponse]:
    return [
        DomainResponse(
            id=d["id"],
            name=d["name"],
            input_features=d["input_features"],
            output_features=d["output_features"],
            n_experiments=len(d["experiments"]),
            created_at=d["created_at"],
        )
        for d in _domains.values()
    ]


@router.get(
    "/{domain_id}",
    response_model=DomainResponse,
    summary="Get domain by ID",
    description="Retrieve the configuration and experiment count for a single domain.",
)
def get_domain(domain_id: str) -> DomainResponse:
    d = _get_or_404(domain_id)
    return DomainResponse(
        id=d["id"],
        name=d["name"],
        input_features=d["input_features"],
        output_features=d["output_features"],
        n_experiments=len(d["experiments"]),
        created_at=d["created_at"],
    )


@router.delete(
    "/{domain_id}",
    status_code=204,
    summary="Delete domain",
    description="Permanently delete a domain and all its associated experiments.",
)
def delete_domain(domain_id: str):
    _get_or_404(domain_id)
    del _domains[domain_id]


def _get_or_404(domain_id: str) -> dict:
    if domain_id not in _domains:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found.")
    return _domains[domain_id]


def get_domain_store() -> dict[str, dict]:
    return _domains
