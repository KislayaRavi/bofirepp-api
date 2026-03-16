from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class ExperimentData(BaseModel):
    data: List[Dict[str, Any]] = Field(
        ...,
        description=(
            "List of experiment records. Each record is a dict mapping "
            "feature keys (both input and output) to their observed values."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {"x1": 0.5, "x2": 1.2, "material": "A", "yield": 0.82, "cost": 12.5},
                    {"x1": 0.3, "x2": -1.0, "material": "B", "yield": 0.74, "cost": 9.8},
                ]
            }
        }
    }


class ExperimentResponse(BaseModel):
    domain_id: str
    n_experiments_added: int
    total_experiments: int
    message: str
