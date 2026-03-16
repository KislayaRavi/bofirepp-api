from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from models.experiment import ExperimentData, ExperimentResponse
from routers.domains import get_domain_store

router = APIRouter(prefix="/domains/{domain_id}/experiments", tags=["Experiments"])


@router.post(
    "",
    response_model=ExperimentResponse,
    status_code=201,
    summary="Add experiments to domain",
    description=(
        "Upload one or more observed experiment results to a domain. "
        "Each record must contain values for all input and output features defined in the domain."
    ),
)
def add_experiments(domain_id: str, payload: ExperimentData) -> ExperimentResponse:
    store = get_domain_store()
    if domain_id not in store:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found.")

    domain = store[domain_id]
    input_keys = {f["key"] for f in domain["input_features"]}
    output_keys = {f["key"] for f in domain["output_features"]}
    required_keys = input_keys | output_keys

    for i, row in enumerate(payload.data):
        missing = required_keys - set(row.keys())
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Row {i} is missing keys: {sorted(missing)}",
            )

    domain["experiments"].extend(payload.data)

    return ExperimentResponse(
        domain_id=domain_id,
        n_experiments_added=len(payload.data),
        total_experiments=len(domain["experiments"]),
        message=f"Successfully added {len(payload.data)} experiment(s). "
                f"Domain now has {len(domain['experiments'])} total experiment(s).",
    )


@router.get(
    "",
    response_model=List[Dict[str, Any]],
    summary="List experiments for domain",
    description="Return all experiment records stored in a domain.",
)
def list_experiments(domain_id: str) -> List[Dict[str, Any]]:
    store = get_domain_store()
    if domain_id not in store:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found.")
    return store[domain_id]["experiments"]


@router.delete(
    "",
    status_code=204,
    summary="Clear all experiments",
    description="Remove all experiment data from a domain without deleting the domain itself.",
)
def clear_experiments(domain_id: str):
    store = get_domain_store()
    if domain_id not in store:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found.")
    store[domain_id]["experiments"] = []
