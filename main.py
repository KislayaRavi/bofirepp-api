import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

# Ensure the app directory is on the path so relative imports work
sys.path.insert(0, os.path.dirname(__file__))

from core.config import settings
from routers import health, domains, experiments, strategies


@asynccontextmanager
async def lifespan(app: FastAPI):
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
            "name": "Domains",
            "description": (
                "Manage optimization domains — define the design space (inputs) "
                "and objectives (outputs) of your experiment."
            ),
        },
        {
            "name": "Experiments",
            "description": "Add and inspect observed experiment results for a domain.",
        },
        {
            "name": "Strategies",
            "description": (
                "Ask the API to suggest the next batch of experiments using a "
                "BoFire optimization strategy (Sobol initialization, Random, or Bayesian BO)."
            ),
        },
    ],
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


app.include_router(health.router)
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
