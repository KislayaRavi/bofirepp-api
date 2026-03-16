from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional

from storage import CampaignStore, get_campaign_store
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


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(campaign_id: str, store: CampaignStore) -> dict:
    c = store.read(campaign_id)
    if c is None:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    return c


def _to_response(c: dict) -> CampaignResponse:
    return CampaignResponse(
        id=c["id"],
        name=c["name"],
        domain=c["domain"],
        strategy=c.get("strategy"),
        context=c.get("context"),
        proposals=c.get("proposals", {}),
        n_experiments=len(c.get("experiments", [])),
        created_at=c["created_at"],
        updated_at=c["updated_at"],
    )


def _to_summary(c: dict) -> CampaignSummary:
    return CampaignSummary(
        id=c["id"],
        name=c["name"],
        has_strategy=c.get("strategy") is not None,
        has_context=c.get("context") is not None,
        n_proposals=len(c.get("proposals", {})),
        n_experiments=len(c.get("experiments", [])),
        created_at=c["created_at"],
        updated_at=c["updated_at"],
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CampaignResponse,
    status_code=201,
    summary="Create campaign",
    description=(
        "Create a new optimization campaign. Each campaign is persisted as a folder on disk "
        "containing a human-readable **campaign.json** file. The folder also holds "
        "**strategy.json** once you call the serialize endpoint.\n\n"
        "A campaign bundles the BoFire domain (design space + objectives), an optional "
        "strategy, optional LLM context, and tracks all proposals and observations over time."
    ),
)
def create_campaign(
    payload: CampaignCreate,
    store: CampaignStore = Depends(get_campaign_store),
) -> CampaignResponse:
    strategy = payload.strategy.model_dump() if payload.strategy else None
    campaign = store.create(
        name=payload.name,
        domain=payload.domain.model_dump(),
        strategy=strategy,
        context=payload.context,
    )
    return _to_response(campaign)


@router.get(
    "",
    response_model=List[CampaignSummary],
    summary="List campaigns",
    description="Return a summary list of all campaigns, newest first.",
)
def list_campaigns(
    store: CampaignStore = Depends(get_campaign_store),
) -> List[CampaignSummary]:
    return [_to_summary(c) for c in store.list_all()]


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign",
    description=(
        "Return the full details of a single campaign. "
        "The data is read directly from **campaign.json** on disk."
    ),
)
def get_campaign(
    campaign_id: str,
    store: CampaignStore = Depends(get_campaign_store),
) -> CampaignResponse:
    return _to_response(_get_or_404(campaign_id, store))


@router.delete(
    "/{campaign_id}",
    status_code=204,
    summary="Delete campaign",
    description="Permanently delete a campaign folder and all files inside it.",
)
def delete_campaign(
    campaign_id: str,
    store: CampaignStore = Depends(get_campaign_store),
):
    _get_or_404(campaign_id, store)
    store.delete(campaign_id)


# ── Strategy setting ──────────────────────────────────────────────────────────

@router.patch(
    "/{campaign_id}/strategy",
    response_model=CampaignResponse,
    summary="Set / update strategy",
    description=(
        "Attach or replace the optimization strategy for this campaign. "
        "Stored under the `strategy` key in **campaign.json**. "
        "The strategy is used whenever you call the generate-proposal endpoint."
    ),
)
def update_strategy(
    campaign_id: str,
    payload: StrategyUpdate,
    store: CampaignStore = Depends(get_campaign_store),
) -> CampaignResponse:
    c = _get_or_404(campaign_id, store)
    c["strategy"] = {"strategy": payload.strategy.value, "n_candidates": payload.n_candidates}
    return _to_response(store.update(c))


# ── Context ───────────────────────────────────────────────────────────────────

@router.patch(
    "/{campaign_id}/context",
    response_model=CampaignResponse,
    summary="Set / update context",
    description=(
        "Attach or update the free-text context that describes the optimization problem. "
        "Stored under the `context` key in **campaign.json**. "
        "This text is intended to be passed to an LLM so it understands what is being optimized."
    ),
)
def update_context(
    campaign_id: str,
    payload: ContextUpdate,
    store: CampaignStore = Depends(get_campaign_store),
) -> CampaignResponse:
    c = _get_or_404(campaign_id, store)
    c["context"] = payload.context
    return _to_response(store.update(c))


# ── Experiments ───────────────────────────────────────────────────────────────

@router.post(
    "/{campaign_id}/experiments",
    response_model=CampaignResponse,
    status_code=201,
    summary="Add experiment observations",
    description=(
        "Record observed experiment results. Appended to the `experiments` list in "
        "**campaign.json**. Bayesian strategies are fitted on these observations when "
        "generating proposals. Each record must include all input and output feature keys."
    ),
)
def add_experiments(
    campaign_id: str,
    payload: ExperimentsAdd,
    store: CampaignStore = Depends(get_campaign_store),
) -> CampaignResponse:
    c = _get_or_404(campaign_id, store)
    domain = c["domain"]
    required_keys = (
        {f["key"] for f in domain["input_features"]}
        | {f["key"] for f in domain["output_features"]}
    )
    for i, row in enumerate(payload.data):
        missing = required_keys - set(row.keys())
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Row {i} is missing keys: {sorted(missing)}",
            )
    c.setdefault("experiments", []).extend(payload.data)
    return _to_response(store.update(c))


@router.get(
    "/{campaign_id}/experiments",
    summary="List experiment observations",
    description="Return all experiment records from **campaign.json**.",
)
def list_experiments(
    campaign_id: str,
    store: CampaignStore = Depends(get_campaign_store),
):
    return _get_or_404(campaign_id, store).get("experiments", [])


@router.delete(
    "/{campaign_id}/experiments",
    status_code=204,
    summary="Clear experiment observations",
    description="Remove all experiment data from the campaign without deleting the campaign folder.",
)
def clear_experiments(
    campaign_id: str,
    store: CampaignStore = Depends(get_campaign_store),
):
    c = _get_or_404(campaign_id, store)
    c["experiments"] = []
    store.update(c)


# ── Proposals ─────────────────────────────────────────────────────────────────

@router.post(
    "/{campaign_id}/proposals/generate",
    response_model=CampaignResponse,
    status_code=201,
    summary="Generate next proposal",
    description=(
        "Use the campaign's strategy to suggest the next batch of experiment candidates. "
        "The first call produces **initial_proposal**, subsequent calls produce **proposal1**, "
        "**proposal2**, and so on. All proposals are stored in **campaign.json**. "
        "Bayesian strategies are fitted on existing observations before generating candidates."
    ),
)
def generate_proposal(
    campaign_id: str,
    payload: ProposalGenerateRequest = ProposalGenerateRequest(),
    store: CampaignStore = Depends(get_campaign_store),
) -> CampaignResponse:
    c = _get_or_404(campaign_id, store)

    strategy_spec = c.get("strategy")
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

    experiments = c.get("experiments", [])
    if strategy_type in BAYESIAN_STRATEGIES and not experiments:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Strategy '{strategy_type.value}' is Bayesian and requires at least one "
                "experiment observation. Add observations via "
                "POST /campaigns/{campaign_id}/experiments first, or switch to 'random'."
            ),
        )

    candidates = _run_strategy(c["domain"], strategy_type, n_candidates, experiments)

    proposals = c.setdefault("proposals", {})
    key = CampaignStore.next_proposal_key(proposals)
    proposals[key] = candidates
    return _to_response(store.update(c))


@router.get(
    "/{campaign_id}/proposals",
    summary="Get all proposals",
    description=(
        "Return the full proposals dict from **campaign.json**. "
        "Keys are 'initial_proposal', 'proposal1', 'proposal2', …"
    ),
)
def get_proposals(
    campaign_id: str,
    store: CampaignStore = Depends(get_campaign_store),
):
    return _get_or_404(campaign_id, store).get("proposals", {})


# ── Serialized BoFire strategy ────────────────────────────────────────────────

@router.post(
    "/{campaign_id}/strategy/serialize",
    status_code=201,
    summary="Serialize and save BoFire strategy",
    description=(
        "Build the full BoFire strategy data model from the campaign's domain and strategy "
        "settings, serialize it to JSON, and save it as **strategy.json** inside the campaign "
        "folder. This file is human-readable and can be used to reproduce the strategy "
        "configuration exactly. Returns the serialized strategy spec."
    ),
)
def serialize_strategy(
    campaign_id: str,
    store: CampaignStore = Depends(get_campaign_store),
) -> Dict[str, Any]:
    c = _get_or_404(campaign_id, store)

    strategy_spec = c.get("strategy")
    if not strategy_spec:
        raise HTTPException(
            status_code=422,
            detail=(
                "This campaign has no strategy set. "
                "Use PATCH /campaigns/{campaign_id}/strategy to set one first."
            ),
        )

    serialized = _build_serialized_strategy(c["domain"], strategy_spec)
    store.save_serialized_strategy(campaign_id, serialized)
    return serialized


@router.get(
    "/{campaign_id}/strategy/serialize",
    summary="Get serialized BoFire strategy",
    description=(
        "Return the contents of **strategy.json** saved in the campaign folder. "
        "Returns 404 if the strategy has not been serialized yet — call "
        "POST /campaigns/{campaign_id}/strategy/serialize first."
    ),
)
def get_serialized_strategy(
    campaign_id: str,
    store: CampaignStore = Depends(get_campaign_store),
) -> Dict[str, Any]:
    _get_or_404(campaign_id, store)
    data = store.read_serialized_strategy(campaign_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No serialized strategy found for this campaign. "
                "Call POST /campaigns/{campaign_id}/strategy/serialize to generate it."
            ),
        )
    return data


# ── BoFire helpers ────────────────────────────────────────────────────────────

def _build_bofire_domain(domain_spec: dict):
    from bofire.data_models.domain.api import Domain
    from bofire.data_models.features.api import (
        ContinuousInput, CategoricalInput, DiscreteInput, ContinuousOutput,
    )
    from bofire.data_models.objectives.api import (
        MinimizeObjective, MaximizeObjective, CloseToTargetObjective,
    )

    bofire_inputs = []
    for f in domain_spec["input_features"]:
        if f["type"] == "continuous":
            bofire_inputs.append(ContinuousInput(key=f["key"], bounds=tuple(f["bounds"])))
        elif f["type"] == "categorical":
            bofire_inputs.append(CategoricalInput(key=f["key"], categories=f["categories"]))
        elif f["type"] == "discrete":
            bofire_inputs.append(DiscreteInput(key=f["key"], values=f["values"]))

    bofire_outputs = []
    for f in domain_spec["output_features"]:
        obj = f.get("objective", "minimize")
        if obj == "minimize":
            objective = MinimizeObjective(w=1.0)
        elif obj == "maximize":
            objective = MaximizeObjective(w=1.0)
        else:
            objective = CloseToTargetObjective(
                target_value=f.get("target_value", 0.0), exponent=1.0, w=1.0
            )
        bofire_outputs.append(ContinuousOutput(key=f["key"], objective=objective))

    return Domain(inputs=bofire_inputs, outputs=bofire_outputs)


def _build_serialized_strategy(domain_spec: dict, strategy_spec: dict) -> dict:
    try:
        from bofire.data_models.strategies.api import (
            RandomStrategy, SoboStrategy, MoboStrategy, QparegoStrategy,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"BoFire not available: {e}",
        )

    strategy_map = {
        StrategyType.random: RandomStrategy,
        StrategyType.sobo: SoboStrategy,
        StrategyType.mobo: MoboStrategy,
        StrategyType.qparego: QparegoStrategy,
    }

    strategy_type = StrategyType(strategy_spec["strategy"])
    StrategyDM = strategy_map[strategy_type]

    try:
        bofire_domain = _build_bofire_domain(domain_spec)
        data_model = StrategyDM(domain=bofire_domain)
        return data_model.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build BoFire strategy spec: {e}",
        )


def _run_strategy(
    domain_spec: dict,
    strategy_type: StrategyType,
    n_candidates: int,
    experiments: list,
) -> list:
    try:
        import bofire.strategies.api as strategies_api
        from bofire.data_models.strategies.api import (
            RandomStrategy, SoboStrategy, MoboStrategy, QparegoStrategy,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"BoFire dependency not available: {e}.",
        )

    strategy_map = {
        StrategyType.random: RandomStrategy,
        StrategyType.sobo: SoboStrategy,
        StrategyType.mobo: MoboStrategy,
        StrategyType.qparego: QparegoStrategy,
    }

    try:
        bofire_domain = _build_bofire_domain(domain_spec)
        StrategyDM = strategy_map[strategy_type]
        strategy_instance = strategies_api.map(StrategyDM(domain=bofire_domain))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize strategy: {e}")

    if experiments:
        try:
            strategy_instance.tell(pd.DataFrame(experiments))
        except Exception as e:
            raise HTTPException(
                status_code=422, detail=f"Failed to fit strategy on experiments: {e}"
            )

    try:
        candidates_df = strategy_instance.ask(candidate_count=n_candidates)
        return candidates_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate candidates: {e}")
