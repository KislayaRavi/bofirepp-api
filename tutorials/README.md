# BoFire++ API — Tutorials

Step-by-step guides covering all major features of the API.
Work through them in order if you are new, or jump to whichever section you need.

| # | File | What you will learn |
|---|------|---------------------|
| 1 | [01_getting_started.md](01_getting_started.md) | Install, run the server, navigate Swagger UI |
| 2 | [02_domain_design.md](02_domain_design.md) | Define input features, output objectives, and design spaces |
| 3 | [03_campaigns.md](03_campaigns.md) | Create and manage a full optimization campaign end-to-end |
| 4 | [04_strategies.md](04_strategies.md) | Choose the right strategy and understand when to switch |
| 5 | [05_llm_integration.md](05_llm_integration.md) | Use the built-in Gemini LLM client from Python |

## Quick reference — base URL

All examples use `http://localhost:8000`. Replace this with your deployed URL if needed.

## Quick reference — endpoints

```
GET  /health                                   Server status
GET  /docs                                     Swagger UI (interactive)
GET  /redoc                                    ReDoc (readable docs)

POST   /campaigns                              Create a campaign
GET    /campaigns                              List all campaigns
GET    /campaigns/{id}                         Get one campaign
DELETE /campaigns/{id}                         Delete a campaign

PATCH  /campaigns/{id}/strategy               Set / update optimization strategy
PATCH  /campaigns/{id}/context                Set / update LLM context text

POST   /campaigns/{id}/experiments            Add experiment observations
GET    /campaigns/{id}/experiments            List observations
DELETE /campaigns/{id}/experiments            Clear all observations

POST   /campaigns/{id}/proposals/generate     Generate next proposal
GET    /campaigns/{id}/proposals              Get all proposals

POST   /campaigns/{id}/strategy/serialize     Serialize strategy → strategy.json
GET    /campaigns/{id}/strategy/serialize     Read strategy.json
```
