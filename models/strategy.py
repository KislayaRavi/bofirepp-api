from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
from enum import Enum


class StrategyType(str, Enum):
    random = "random"
    sobo = "sobo"
    mobo = "mobo"
    qparego = "qparego"


class SuggestRequest(BaseModel):
    strategy: StrategyType = Field(
        StrategyType.random,
        description=(
            "Which optimization strategy to use:\n"
            "- **random**: Uniform random sampling — no prior data needed, good for initial exploration.\n"
            "- **sobo**: Single-Objective Bayesian Optimization (BoTorch-based) — requires at least a few observations.\n"
            "- **mobo**: Multi-Objective Bayesian Optimization (qEHVI) — requires at least a few observations and multiple output features.\n"
            "- **qparego**: qParEGO scalarization for multi-objective BO — requires at least a few observations."
        ),
    )
    n_candidates: int = Field(
        1, ge=1, le=100, description="Number of candidate experiments to suggest"
    )
    strategy_options: Optional[Dict[str, Any]] = Field(
        None, description="Optional strategy-specific hyperparameters (reserved for future use)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "strategy": "random",
                "n_candidates": 5,
                "strategy_options": None,
            }
        }
    }


class SuggestResponse(BaseModel):
    domain_id: str
    strategy: str
    n_candidates: int
    candidates: List[Dict[str, Any]]
    message: str
