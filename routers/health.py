from fastapi import APIRouter
from pydantic import BaseModel
import platform
import sys

router = APIRouter(prefix="/health", tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    version: str
    python_version: str
    bofire_available: bool


@router.get(
    "",
    response_model=HealthStatus,
    summary="Health check",
    description="Returns the health status of the API and checks that BoFire is importable.",
)
def health_check():
    try:
        import bofire  # noqa: F401
        bofire_ok = True
    except ImportError:
        bofire_ok = False

    return HealthStatus(
        status="ok",
        version="0.1.0",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        bofire_available=bofire_ok,
    )
