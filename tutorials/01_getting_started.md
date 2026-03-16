# Tutorial 1 — Getting Started

This tutorial shows how to install the dependencies, start the server, and make your first API call.

---

## 1. Install dependencies

```bash
cd artifacts/bofire-api

# Core API (FastAPI, Pydantic, uvicorn)
pip install .

# Add BoFire + PyTorch + BoTorch for Bayesian strategies
pip install ".[optimization]"

# Add developer tools (pytest, ruff, mypy)
pip install ".[dev]"
```

> The BoFire optimization extras pull in PyTorch and BoTorch, which are large downloads.
> If you only need random sampling, the core install is sufficient.

---

## 2. Configure storage (optional)

Campaigns are stored as folders on disk. The default root is `./campaigns_data/`.
Override it with an environment variable:

```bash
export DATABASE_PATH=/data/my_campaigns   # Linux / macOS
set DATABASE_PATH=C:\data\my_campaigns    # Windows
```

---

## 3. Start the server

```bash
uvicorn main:app --reload
# or
python main.py
```

The server starts on `http://localhost:8000`.
Opening that URL in a browser redirects you directly to `/docs`.

---

## 4. Swagger UI

Navigate to `http://localhost:8000/docs`.

You will see every endpoint listed with its description, request schema, and an interactive **Try it out** button.
This is the fastest way to explore the API without writing any code.

ReDoc (read-only, more readable) is at `http://localhost:8000/redoc`.

---

## 5. Health check

Confirm the server is running:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "app_name": "BoFire++ API",
  "version": "0.1.0",
  "python_version": "3.11.x",
  "bofire_available": true
}
```

If `bofire_available` is `false`, Bayesian strategy endpoints will return `503`.
Install the optimization extras to fix this.

---

## 6. Your first campaign (one command)

```bash
curl -s -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hello BoFire",
    "domain": {
      "name": "Simple 2D problem",
      "input_features": [
        {"key": "x1", "type": "continuous", "bounds": [0.0, 1.0]},
        {"key": "x2", "type": "continuous", "bounds": [0.0, 1.0]}
      ],
      "output_features": [
        {"key": "y", "type": "continuous", "objective": "minimize"}
      ]
    },
    "strategy": {"strategy": "random", "n_candidates": 3}
  }' | python3 -m json.tool
```

The response includes the campaign `id` — save it, you will need it for follow-up calls.

---

## Next steps

- **[Tutorial 2 — Domain Design](02_domain_design.md)**: learn how to model any real-world problem as a BoFire domain.
- **[Tutorial 3 — Campaigns](03_campaigns.md)**: run a full optimization loop from start to finish.
