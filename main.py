import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

# Ensure the app directory is on the path so relative imports work
sys.path.insert(0, os.path.dirname(__file__))

from core.config import settings
from database import init_db
from routers import health, domains, experiments, strategies
from routers import campaigns


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise SQLite database and create tables
    init_db()
    print(f"Starting {settings.app_name} v{settings.app_version}")
    try:
        import bofire
        print(f"BoFire version: {bofire.__version__}")
    except ImportError:
        print("WARNING: BoFire not installed — strategy endpoints will return 503.")
    yield
    print("Shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "BoFire++",
        "url": "https://github.com/KislayaRavi/bofirepp-api",
    },
    license_info={
        "name": "BSD 3-Clause",
        "url": "https://opensource.org/licenses/BSD-3-Clause",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Server health and diagnostics.",
        },
        {
            "name": "Campaigns",
            "description": (
                "A **Campaign** is the top-level container for an optimization problem. "
                "It holds the BoFire domain (design space + objectives), an optional strategy, "
                "optional LLM context, all experiment observations, and a full history of proposals. "
                "All optimization work should be done through campaigns."
            ),
        },
        {
            "name": "Domains",
            "description": (
                "Low-level domain management — define the design space (inputs) "
                "and objectives (outputs) without a full campaign. "
                "Prefer using Campaigns for end-to-end optimization workflows."
            ),
        },
        {
            "name": "Experiments",
            "description": "Add and inspect observed experiment results for a standalone domain.",
        },
        {
            "name": "Strategies",
            "description": (
                "Low-level strategy execution on a standalone domain. "
                "Prefer using Campaign proposals for tracked workflows."
            ),
        },
    ],
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


app.include_router(health.router)
app.include_router(campaigns.router)
app.include_router(domains.router)
app.include_router(experiments.router)
app.include_router(strategies.router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", settings.port))
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=port,
        reload=settings.debug,
    )
