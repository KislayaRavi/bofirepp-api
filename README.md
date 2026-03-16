# BoFire++ API

A **FastAPI** REST service wrapping [BoFire](https://github.com/experimental-design/bofire) — the Bayesian optimization framework — with auto-generated **Swagger UI** and **ReDoc** documentation.

## Features

- **Swagger UI** at `/docs` and **ReDoc** at `/redoc`
- Domain management — define design spaces with continuous, categorical, and discrete input features
- Experiment tracking — upload observed results to a domain
- Strategy-based candidate suggestion:
  - `sobol` — Sobol sequence initialization (no prior data needed)
  - `random` — uniform random initialization (no prior data needed)
  - `botorch_qNEI` — qNoisyExpectedImprovement (single-objective BO)
  - `botorch_qEHVI` — qExpectedHypervolumeImprovement (multi-objective BO)
  - `botorch_qParEGO` — qParEGO scalarization (multi-objective BO)

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the server

```bash
uvicorn main:app --reload
# or
python main.py
```

Server starts at `http://localhost:8000` and immediately redirects `/` → `/docs`.

### 3. Try the Swagger UI

Open `http://localhost:8000/docs` to explore and call all endpoints interactively.

## API Workflow

```
POST /domains              → create a domain (define design space + objectives)
POST /domains/{id}/experiments  → upload observed experiment data
POST /domains/{id}/suggest      → ask for the next experiments to run
```

### Example: Sobol initialization

```bash
# 1. Create a domain
curl -X POST http://localhost:8000/domains \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Problem",
    "input_features": [
      {"key": "x1", "type": "continuous", "bounds": [0.0, 1.0]},
      {"key": "x2", "type": "continuous", "bounds": [-5.0, 5.0]}
    ],
    "output_features": [
      {"key": "y", "type": "continuous", "objective": "minimize"}
    ]
  }'

# 2. Ask for 5 Sobol candidates (no prior data needed)
curl -X POST http://localhost:8000/domains/{domain_id}/suggest \
  -H "Content-Type: application/json" \
  -d '{"strategy": "sobol", "n_candidates": 5}'
```

## Project Structure

```
bofire-api/
├── main.py            # FastAPI app + router registration
├── requirements.txt   # Python dependencies
├── core/
│   └── config.py      # App settings (pydantic-settings)
├── models/
│   ├── domain.py      # Domain create/response schemas
│   ├── experiment.py  # Experiment data schemas
│   └── strategy.py    # Strategy request/response schemas
└── routers/
    ├── health.py      # GET /health
    ├── domains.py     # CRUD for /domains
    ├── experiments.py # POST/GET /domains/{id}/experiments
    └── strategies.py  # POST /domains/{id}/suggest
```

## Configuration

| Environment Variable | Default     | Description            |
|----------------------|-------------|------------------------|
| `PORT`               | `8000`      | Port to bind           |
| `DEBUG`              | `false`     | Enable auto-reload     |

## Dependencies

- [FastAPI](https://fastapi.tiangolo.com/) — web framework
- [Uvicorn](https://www.uvicorn.org/) — ASGI server
- [BoFire](https://github.com/experimental-design/bofire) — Bayesian optimization
- [Pydantic v2](https://docs.pydantic.dev/) — data validation

## License

BSD 3-Clause — same as BoFire.
