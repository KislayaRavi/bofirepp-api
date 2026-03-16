from fastapi import APIRouter, HTTPException
import pandas as pd

from models.strategy import SuggestRequest, SuggestResponse, StrategyType
from routers.domains import get_domain_store

router = APIRouter(prefix="/domains/{domain_id}/suggest", tags=["Strategies"])

BAYESIAN_STRATEGIES = (StrategyType.sobo, StrategyType.mobo, StrategyType.qparego)


@router.post(
    "",
    response_model=SuggestResponse,
    summary="Suggest next experiments",
    description=(
        "Use the specified optimization strategy to propose the next batch of experiments to run.\n\n"
        "**Initialization strategies** (`random`) work without any prior data and are ideal for the first round.\n\n"
        "**Bayesian strategies** (`sobo`, `mobo`, `qparego`) require at least a few observations "
        "to fit a surrogate model. Use `POST /domains/{domain_id}/experiments` to add observations first."
    ),
)
def suggest(domain_id: str, payload: SuggestRequest) -> SuggestResponse:
    store = get_domain_store()
    if domain_id not in store:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found.")

    domain = store[domain_id]
    experiments = domain["experiments"]

    # Guard: Bayesian strategies need training data
    if payload.strategy in BAYESIAN_STRATEGIES and not experiments:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Strategy '{payload.strategy}' is a Bayesian method and requires at least "
                "one experiment observation to fit a surrogate model. "
                "Use 'random' for the initial design phase, or add observations via "
                "POST /domains/{domain_id}/experiments first."
            ),
        )

    try:
        from bofire.data_models.domain.api import Domain
        from bofire.data_models.features.api import (
            ContinuousInput,
            CategoricalInput,
            DiscreteInput,
            ContinuousOutput,
        )
        from bofire.data_models.objectives.api import (
            MinimizeObjective,
            MaximizeObjective,
            CloseToTargetObjective,
        )
        import bofire.strategies.api as strategies_api
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"BoFire dependency not available: {e}. "
                "Please install all BoFire extras: pip install 'bofire[optimization]'"
            ),
        )

    # Build BoFire input features
    bofire_inputs = []
    for f in domain["input_features"]:
        if f["type"] == "continuous":
            bofire_inputs.append(
                ContinuousInput(key=f["key"], bounds=(f["bounds"][0], f["bounds"][1]))
            )
        elif f["type"] == "categorical":
            bofire_inputs.append(
                CategoricalInput(key=f["key"], categories=f["categories"])
            )
        elif f["type"] == "discrete":
            bofire_inputs.append(
                DiscreteInput(key=f["key"], values=f["values"])
            )

    # Build BoFire output features
    bofire_outputs = []
    for f in domain["output_features"]:
        obj_type = f.get("objective", "minimize")
        if obj_type == "minimize":
            objective = MinimizeObjective(w=1.0)
        elif obj_type == "maximize":
            objective = MaximizeObjective(w=1.0)
        else:
            target = f.get("target_value", 0.0)
            objective = CloseToTargetObjective(target_value=target, exponent=1.0, w=1.0)
        bofire_outputs.append(ContinuousOutput(key=f["key"], objective=objective))

    bofire_domain = Domain(inputs=bofire_inputs, outputs=bofire_outputs)

    # Initialize strategy
    try:
        StrategyDataModel = _get_strategy_data_model(payload.strategy)
        strategy_data_model = StrategyDataModel(domain=bofire_domain)
        strategy_instance = strategies_api.map(strategy_data_model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize strategy: {e}")

    # Fit on existing data if available
    if experiments:
        df = pd.DataFrame(experiments)
        try:
            strategy_instance.tell(df)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Failed to fit strategy on existing experiment data: {e}",
            )

    # Generate candidates
    try:
        candidates_df = strategy_instance.ask(candidate_count=payload.n_candidates)
        candidates = candidates_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate candidates: {e}")

    return SuggestResponse(
        domain_id=domain_id,
        strategy=payload.strategy.value,
        n_candidates=len(candidates),
        candidates=candidates,
        message=(
            f"Generated {len(candidates)} candidate experiment(s) using "
            f"'{payload.strategy.value}' strategy."
        ),
    )


def _get_strategy_data_model(strategy: StrategyType):
    from bofire.data_models.strategies.api import (
        RandomStrategy,
        SoboStrategy,
        MoboStrategy,
        QparegoStrategy,
    )

    mapping = {
        StrategyType.random: RandomStrategy,
        StrategyType.sobo: SoboStrategy,
        StrategyType.mobo: MoboStrategy,
        StrategyType.qparego: QparegoStrategy,
    }

    if strategy not in mapping:
        raise ValueError(f"Unknown strategy: {strategy}")
    return mapping[strategy]
