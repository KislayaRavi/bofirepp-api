from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union, Annotated
from enum import Enum


class ObjectiveType(str, Enum):
    minimize = "minimize"
    maximize = "maximize"
    close_to_target = "close_to_target"


class ContinuousInputFeature(BaseModel):
    key: str = Field(..., description="Unique name of the feature")
    type: Literal["continuous"] = "continuous"
    bounds: List[float] = Field(..., min_length=2, max_length=2, description="[lower, upper] bounds")


class CategoricalInputFeature(BaseModel):
    key: str = Field(..., description="Unique name of the feature")
    type: Literal["categorical"] = "categorical"
    categories: List[str] = Field(..., description="List of valid category strings")


class DiscreteInputFeature(BaseModel):
    key: str = Field(..., description="Unique name of the feature")
    type: Literal["discrete"] = "discrete"
    values: List[float] = Field(..., description="List of allowed discrete values")


InputFeature = Annotated[
    Union[ContinuousInputFeature, CategoricalInputFeature, DiscreteInputFeature],
    Field(discriminator="type"),
]


class ContinuousOutputFeature(BaseModel):
    key: str = Field(..., description="Unique name of the output feature")
    type: Literal["continuous"] = "continuous"
    objective: ObjectiveType = Field(
        ObjectiveType.minimize, description="Optimization objective for this output"
    )
    target_value: Optional[float] = Field(
        None, description="Target value (required if objective is close_to_target)"
    )


OutputFeature = ContinuousOutputFeature


class DomainCreate(BaseModel):
    name: str = Field(..., description="Human-readable name for the optimization domain")
    input_features: List[InputFeature] = Field(
        ..., description="List of input features describing the design space"
    )
    output_features: List[OutputFeature] = Field(
        ..., description="List of output features (objectives) to optimize"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "My Optimization Problem",
                "input_features": [
                    {"key": "x1", "type": "continuous", "bounds": [0.0, 1.0]},
                    {"key": "x2", "type": "continuous", "bounds": [-5.0, 5.0]},
                    {"key": "material", "type": "categorical", "categories": ["A", "B", "C"]},
                ],
                "output_features": [
                    {"key": "yield", "type": "continuous", "objective": "maximize"},
                    {"key": "cost", "type": "continuous", "objective": "minimize"},
                ],
            }
        }
    }


class DomainResponse(BaseModel):
    id: str
    name: str
    input_features: List[InputFeature]
    output_features: List[OutputFeature]
    n_experiments: int = 0
    created_at: str
