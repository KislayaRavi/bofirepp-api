# Tutorial 3 — Campaigns

A **campaign** is the top-level container for an optimization problem.
It bundles the domain definition, strategy, experiment history, and all generated proposals in a single folder on disk.

This tutorial walks through a complete optimization loop from scratch.

---

## What is stored on disk

Each campaign lives at `{DATABASE_PATH}/{campaign_id}/`:

```
campaigns_data/
  3f8a21bc-…/
    campaign.json     ← all campaign data in human-readable JSON
    strategy.json     ← serialized BoFire strategy spec (written on demand)
```

You can open `campaign.json` in any text editor to inspect or audit the full history.

---

## Step 1 — Create the campaign

```bash
curl -s -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Polymer yield optimization",
    "domain": {
      "name": "Polymer synthesis reactor",
      "input_features": [
        {"key": "temperature", "type": "continuous",  "bounds": [80.0, 220.0]},
        {"key": "time",        "type": "continuous",  "bounds": [1.0, 10.0]},
        {"key": "catalyst",    "type": "categorical", "categories": ["Cat-A", "Cat-B", "Cat-C"]}
      ],
      "output_features": [
        {"key": "yield", "type": "continuous", "objective": "maximize"}
      ]
    },
    "strategy": {"strategy": "random", "n_candidates": 4},
    "context": "Optimizing a free-radical polymerization. Temperature and time are the dominant factors."
  }'
```

Note the `id` field in the response — set it as an environment variable for convenience:

```bash
export CID="<campaign-id-from-response>"
```

---

## Step 2 — Generate the initial proposal (random exploration)

The first call always uses the strategy as configured.
With `"random"` you get candidates without needing any prior data.

```bash
curl -s -X POST http://localhost:8000/campaigns/$CID/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{}'
```

The response shows the campaign with the new `initial_proposal` key inside `proposals`:

```json
{
  "proposals": {
    "initial_proposal": [
      {"temperature": 143.2, "time": 5.6, "catalyst": "Cat-B"},
      {"temperature": 97.4,  "time": 3.1, "catalyst": "Cat-A"},
      ...
    ]
  }
}
```

Run these experiments in your lab / simulator.

---

## Step 3 — Record observations

After running the proposed experiments, submit the measured outputs:

```bash
curl -s -X POST http://localhost:8000/campaigns/$CID/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"temperature": 143.2, "time": 5.6, "catalyst": "Cat-B", "yield": 0.72},
      {"temperature": 97.4,  "time": 3.1, "catalyst": "Cat-A", "yield": 0.61},
      {"temperature": 180.0, "time": 7.2, "catalyst": "Cat-C", "yield": 0.68},
      {"temperature": 110.0, "time": 4.0, "catalyst": "Cat-B", "yield": 0.75}
    ]
  }'
```

Each row must include values for **all** input and output feature keys.

---

## Step 4 — Switch to Bayesian optimization

Now that you have data, switch to a Bayesian strategy to exploit what has been learned:

```bash
curl -s -X PATCH http://localhost:8000/campaigns/$CID/strategy \
  -H "Content-Type: application/json" \
  -d '{"strategy": "sobo", "n_candidates": 3}'
```

---

## Step 5 — Generate the next Bayesian proposal

```bash
curl -s -X POST http://localhost:8000/campaigns/$CID/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{}'
```

The response now contains `proposal1` (the second round):

```json
{
  "proposals": {
    "initial_proposal": [...],
    "proposal1": [
      {"temperature": 195.0, "time": 8.3, "catalyst": "Cat-B"},
      ...
    ]
  }
}
```

---

## Step 6 — Repeat

Add more observations → generate another proposal → repeat until satisfied.

```
initial_proposal  →  add experiments  →  proposal1  →  add experiments  →  proposal2  →  …
```

Each `POST /proposals/generate` appends the next proposal key automatically:
`initial_proposal`, `proposal1`, `proposal2`, `proposal3`, …

---

## Step 7 — Inspect the campaign at any time

```bash
# Full campaign (domain, strategy, all proposals, experiment count)
curl -s http://localhost:8000/campaigns/$CID | python3 -m json.tool

# Just the proposals
curl -s http://localhost:8000/campaigns/$CID/proposals | python3 -m json.tool

# Just the observations
curl -s http://localhost:8000/campaigns/$CID/experiments | python3 -m json.tool
```

---

## Step 8 — Serialize the strategy (optional)

Save the full BoFire strategy configuration as `strategy.json` in the campaign folder:

```bash
curl -s -X POST http://localhost:8000/campaigns/$CID/strategy/serialize | python3 -m json.tool
```

Read it back later:

```bash
curl -s http://localhost:8000/campaigns/$CID/strategy/serialize | python3 -m json.tool
```

---

## Step 9 — Clean up

```bash
# Clear only observations (keep proposals and domain)
curl -X DELETE http://localhost:8000/campaigns/$CID/experiments

# Delete the entire campaign folder
curl -X DELETE http://localhost:8000/campaigns/$CID
```

---

## List all campaigns

```bash
curl -s http://localhost:8000/campaigns | python3 -m json.tool
```

Returns a summary list (newest first) with counts of proposals and experiments for each campaign.

---

## Next steps

- **[Tutorial 4 — Strategies](04_strategies.md)**: understand when to use `random`, `sobo`, `mobo`, or `qparego`.
- **[Tutorial 5 — LLM Integration](05_llm_integration.md)**: use Gemini to reason about campaign results.
