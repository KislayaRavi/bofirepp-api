from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from db.models import Campaign
from models.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignSummary,
    ContextUpdate,
    ExperimentsAdd,
    ProposalGenerateRequest,
    StrategyUpdate,
)
from models.strategy import StrategyType

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

BAYESIAN_STRATEGIES = (StrategyType.sobo, StrategyType.mobo, StrategyType.qparego)


# ── helpers ──────────────────────────────────────────────────────────────────

def _campaign_or_404(campaign_id: str, db: Session) -> Campaign:
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    return c


def _to_response(c: Campaign) -> CampaignResponse:
    return CampaignResponse(
        id=c.id,
        name=c.name,
        domain=c.get_domain(),
        strategy=c.get_strategy(),
        context=c.context,
        proposals=c.get_proposals(),
        n_experiments=len(c.get_experiments()),
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _to_summary(c: Campaign) -> CampaignSummary:
    return CampaignSummary(
        id=c.id,
        name=c.name,
        has_strategy=c.strategy_json is not None,
        has_context=c.context is not None,
        n_proposals=len(c.get_proposals()),
        n_experiments=len(c.get_experiments()),
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CampaignResponse,
    status_code=201,
    summary="Create campaign",
    description=(
        "Create a new optimization campaign. A campaign bundles together the BoFire domain "
        "(design space + objectives), an optional strategy, optional LLM context, and tracks "
        "all proposals and experiment observations over time."
    ),
)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)) -> CampaignResponse:
    strategy_json = None
    if payload.strategy:
        strategy_json = payload.strategy.model_dump_json()

    campaign = Campaign(
        id=str(uuid4()),
        name=payload.name,
        domain_json=payload.domain.model_dump_json(),
        strategy_json=strategy_json,
        context=payload.context,
        proposals_json="{}",
        experiments_json="[]",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _to_response(campaign)


@router.get(
    "",
    response_model=List[CampaignSummary],
    summary="List campaigns",
    description="Return a summary list of all campaigns.",
)
def list_campaigns(db: Session = Depends(get_db)) -> List[CampaignSummary]:
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return [_to_summary(c) for c in campaigns]


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign",
    description="Return the full details of a single campaign including all proposals and experiment count.",
)
def get_campaign(campaign_id: str, db: Session = Depends(get_db)) -> CampaignResponse:
    return _to_response(_campaign_or_404(campaign_id, db))


@router.delete(
    "/{campaign_id}",
    status_code=204,
    summary="Delete campaign",
    description="Permanently delete a campaign and all its associated data.",
)
def delete_campaign(campaign_id: str, db: Session = Depends(get_db)):
    c = _campaign_or_404(campaign_id, db)
    db.delete(c)
    db.commit()


# ── Strategy ─────────────────────────────────────────────────────────────────

@router.patch(
    "/{campaign_id}/strategy",
    response_model=CampaignResponse,
    summary="Set / update strategy",
    description=(
        "Attach or replace the optimization strategy for this campaign. "
        "The strategy is used whenever you call the generate-proposal endpoint."
    ),
)
def update_strategy(
    campaign_id: str, payload: StrategyUpdate, db: Session = Depends(get_db)
) -> CampaignResponse:
    c = _campaign_or_404(campaign_id, db)
    c.strategy_json = json.dumps(
        {"strategy": payload.strategy.value, "n_candidates": payload.n_candidates}
    )
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return _to_response(c)


# ── Context ───────────────────────────────────────────────────────────────────

@router.patch(
    "/{campaign_id}/context",
    response_model=CampaignResponse,
    summary="Set / update context",
    description=(
        "Attach or update the free-text context that describes the optimization problem. "
        "This text is intended to be passed to an LLM so it understands what is being optimized."
    ),
)
def update_context(
    campaign_id: str, payload: ContextUpdate, db: Session = Depends(get_db)
) -> CampaignResponse:
    c = _campaign_or_404(campaign_id, db)
    c.context = payload.context
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return _to_response(c)


# ── Experiments ───────────────────────────────────────────────────────────────

@router.post(
    "/{campaign_id}/experiments",
    response_model=CampaignResponse,
    status_code=201,
    summary="Add experiment observations",
    description=(
        "Record observed experiment results inside the campaign. "
        "These observations are used to fit the surrogate model when generating Bayesian proposals. "
        "Each record must contain values for all input and output features defined in the domain."
    ),
)
def add_experiments(
    campaign_id: str, payload: ExperimentsAdd, db: Session = Depends(get_db)
) -> CampaignResponse:
    c = _campaign_or_404(campaign_id, db)
    domain = c.get_domain()
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

    experiments = c.get_experiments()
    experiments.extend(payload.data)
    c.set_experiments(experiments)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return _to_response(c)


@router.get(
    "/{campaign_id}/experiments",
    summary="List experiment observations",
    description="Return all experiment records stored in this campaign.",
)
def list_experiments(campaign_id: str, db: Session = Depends(get_db)):
    c = _campaign_or_404(campaign_id, db)
    return c.get_experiments()


@router.delete(
    "/{campaign_id}/experiments",
    status_code=204,
    summary="Clear experiment observations",
    description="Remove all experiment data from the campaign without deleting it.",
)
def clear_experiments(campaign_id: str, db: Session = Depends(get_db)):
    c = _campaign_or_404(campaign_id, db)
    c.set_experiments([])
    c.updated_at = datetime.now(timezone.utc)
    db.commit()


# ── Proposals ─────────────────────────────────────────────────────────────────

@router.post(
    "/{campaign_id}/proposals/generate",
    response_model=CampaignResponse,
    status_code=201,
    summary="Generate next proposal",
    description=(
        "Use the campaign's strategy to suggest the next batch of experiment candidates. "
        "The first call produces **initial_proposal**, subsequent calls produce **proposal1**, "
        "**proposal2**, and so on. Bayesian strategies are fitted on all existing observations "
        "before generating candidates."
    ),
)
def generate_proposal(
    campaign_id: str,
    payload: ProposalGenerateRequest = ProposalGenerateRequest(),
    db: Session = Depends(get_db),
) -> CampaignResponse:
    c = _campaign_or_404(campaign_id, db)

    strategy_spec = c.get_strategy()
    if not strategy_spec:
        raise HTTPException(
            status_code=422,
            detail=(
                "This campaign has no strategy set. "
                "Use PATCH /campaigns/{campaign_id}/strategy to add one first."
            ),
        )

    strategy_type = StrategyType(strategy_spec["strategy"])
    n_candidates = payload.n_candidates or strategy_spec.get("n_candidates", 1)

    experiments = c.get_experiments()
    if strategy_type in BAYESIAN_STRATEGIES and not experiments:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Strategy '{strategy_type.value}' is Bayesian and requires at least one "
                "experiment observation. Add observations via "
                "POST /campaigns/{campaign_id}/experiments first, or switch to 'random'."
            ),
        )

    candidates = _run_strategy(c.get_domain(), strategy_type, n_candidates, experiments)

    proposals = c.get_proposals()
    key = c.next_proposal_key()
    proposals[key] = candidates
    c.set_proposals(proposals)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return _to_response(c)


@router.get(
    "/{campaign_id}/proposals",
    summary="Get all proposals",
    description=(
        "Return the full proposals dict for this campaign. "
        "Keys are 'initial_proposal', 'proposal1', 'proposal2', …"
    ),
)
def get_proposals(campaign_id: str, db: Session = Depends(get_db)):
    c = _campaign_or_404(campaign_id, db)
    return c.get_proposals()


# ── BoFire strategy execution ─────────────────────────────────────────────────

def _run_strategy(
    domain_spec: dict,
    strategy_type: StrategyType,
    n_candidates: int,
    experiments: list,
) -> list:
    try:
        from bofire.data_models.domain.api import Domain
        from bofire.data_models.features.api import (
            ContinuousInput, CategoricalInput, DiscreteInput, ContinuousOutput,
        )
        from bofire.data_models.objectives.api import (
            MinimizeObjective, MaximizeObjective, CloseToTargetObjective,
        )
        import bofire.strategies.api as strategies_api
        from bofire.data_models.strategies.api import (
            RandomStrategy, SoboStrategy, MoboStrategy, QparegoStrategy,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"BoFire dependency not available: {e}. Install with: pip install 'bofire[optimization]'",
        )

    # Build inputs
    bofire_inputs = []
    for f in domain_spec["input_features"]:
        if f["type"] == "continuous":
            bofire_inputs.append(ContinuousInput(key=f["key"], bounds=tuple(f["bounds"])))
        elif f["type"] == "categorical":
            bofire_inputs.append(CategoricalInput(key=f["key"], categories=f["categories"]))
        elif f["type"] == "discrete":
            bofire_inputs.append(DiscreteInput(key=f["key"], values=f["values"]))

    # Build outputs
    bofire_outputs = []
    for f in domain_spec["output_features"]:
        obj = f.get("objective", "minimize")
        if obj == "minimize":
            objective = MinimizeObjective(w=1.0)
        elif obj == "maximize":
            objective = MaximizeObjective(w=1.0)
        else:
            objective = CloseToTargetObjective(target_value=f.get("target_value", 0.0), exponent=1.0, w=1.0)
        bofire_outputs.append(ContinuousOutput(key=f["key"], objective=objective))

    bofire_domain = Domain(inputs=bofire_inputs, outputs=bofire_outputs)

    strategy_map = {
        StrategyType.random: RandomStrategy,
        StrategyType.sobo: SoboStrategy,
        StrategyType.mobo: MoboStrategy,
        StrategyType.qparego: QparegoStrategy,
    }

    try:
        StrategyDM = strategy_map[strategy_type]
        strategy_instance = strategies_api.map(StrategyDM(domain=bofire_domain))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize strategy: {e}")

    if experiments:
        try:
            strategy_instance.tell(pd.DataFrame(experiments))
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to fit strategy on experiments: {e}")

    try:
        candidates_df = strategy_instance.ask(candidate_count=n_candidates)
        return candidates_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate candidates: {e}")
