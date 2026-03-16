from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from models.domain import DomainCreate
from models.strategy import SuggestRequest, StrategyType


class CampaignCreate(BaseModel):
    name: str = Field(..., description="Human-readable name for this optimization campaign")
    domain: DomainCreate = Field(..., description="BoFire domain — defines the design space and objectives")
    strategy: Optional[SuggestRequest] = Field(
        None, description="Optimization strategy to use when generating proposals (can be set later)"
    )
    context: Optional[str] = Field(
        None,
        description=(
            "Free-text description of the optimization problem. "
            "Used to give an LLM context about what is being optimized."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Polymer synthesis yield optimization",
                "domain": {
                    "name": "Polymer Synthesis",
                    "input_features": [
                        {"key": "temperature", "type": "continuous", "bounds": [50.0, 200.0]},
                        {"key": "pressure", "type": "continuous", "bounds": [1.0, 10.0]},
                        {"key": "catalyst", "type": "categorical", "categories": ["Cat-A", "Cat-B", "Cat-C"]},
                    ],
                    "output_features": [
                        {"key": "yield", "type": "continuous", "objective": "maximize"},
                        {"key": "purity", "type": "continuous", "objective": "maximize"},
                    ],
                },
                "strategy": {"strategy": "random", "n_candidates": 5},
                "context": (
                    "We are optimizing a polymer synthesis reaction. "
                    "Higher yield and purity are both desired. "
                    "The catalyst type significantly affects selectivity."
                ),
            }
        }
    }


class StrategyUpdate(BaseModel):
    strategy: StrategyType = Field(..., description="Strategy type to use")
    n_candidates: int = Field(1, ge=1, le=100, description="Number of candidates per proposal")

    model_config = {
        "json_schema_extra": {
            "example": {"strategy": "sobo", "n_candidates": 3}
        }
    }


class ContextUpdate(BaseModel):
    context: str = Field(
        ...,
        description="Free-text description of the optimization problem for LLM context",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "context": (
                    "We are running a drug discovery campaign targeting enzyme inhibition. "
                    "The goal is to maximize inhibitory activity while minimizing toxicity."
                )
            }
        }
    }


class ExperimentsAdd(BaseModel):
    data: List[Dict[str, Any]] = Field(
        ...,
        description=(
            "List of observed experiment results to add to this campaign. "
            "Each record must contain values for all input and output features in the domain."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {"temperature": 120.0, "pressure": 3.5, "catalyst": "Cat-A", "yield": 0.78, "purity": 0.91},
                    {"temperature": 160.0, "pressure": 6.0, "catalyst": "Cat-B", "yield": 0.84, "purity": 0.87},
                ]
            }
        }
    }


class ProposalGenerateRequest(BaseModel):
    n_candidates: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description=(
            "Number of candidates to generate. "
            "If omitted, uses the value from the campaign's strategy setting."
        ),
    )

    model_config = {
        "json_schema_extra": {"example": {"n_candidates": 5}}
    }


class CampaignResponse(BaseModel):
    id: str
    name: str
    domain: Dict[str, Any]
    strategy: Optional[Dict[str, Any]]
    context: Optional[str]
    proposals: Dict[str, Any]
    n_experiments: int
    created_at: str
    updated_at: str


class CampaignSummary(BaseModel):
    id: str
    name: str
    has_strategy: bool
    has_context: bool
    n_proposals: int
    n_experiments: int
    created_at: str
    updated_at: str
