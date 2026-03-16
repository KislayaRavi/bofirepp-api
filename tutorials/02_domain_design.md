# Tutorial 2 — Domain Design

A **domain** defines the optimization problem: what you can control (input features) and what you want to improve (output features).
Getting the domain right is the most important step before running any strategy.

---

## Input feature types

### Continuous

A real-valued parameter with a lower and upper bound.
Use this for temperature, concentration, time, pH, flow rate, etc.

```json
{"key": "temperature", "type": "continuous", "bounds": [50.0, 200.0]}
```

### Categorical

A finite set of unordered options.
Use this for catalyst type, solvent, material, machine setting, etc.

```json
{"key": "catalyst", "type": "categorical", "categories": ["Cat-A", "Cat-B", "Cat-C"]}
```

### Discrete

A finite ordered set of numeric values.
Use this for batch size, number of cycles, integer pH steps, etc.

```json
{"key": "rpm", "type": "discrete", "values": [200, 400, 600, 800, 1000]}
```

---

## Output feature objectives

All outputs must be continuous. Choose one objective per output:

| `objective` | Meaning |
|-------------|---------|
| `"minimize"` | Lower is better (e.g. cost, reaction time, defect rate) |
| `"maximize"` | Higher is better (e.g. yield, purity, strength) |
| `"close_to_target"` | Aim for a specific numeric value (e.g. target pH = 7.4) |

```json
{"key": "yield",        "type": "continuous", "objective": "maximize"}
{"key": "cost",         "type": "continuous", "objective": "minimize"}
{"key": "ph",           "type": "continuous", "objective": "close_to_target", "target_value": 7.4}
```

---

## Single-objective example — reaction yield

Maximize yield by tuning temperature, pressure, and catalyst type.

```bash
curl -s -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Reaction yield optimization",
    "domain": {
      "name": "Reactor conditions",
      "input_features": [
        {"key": "temperature", "type": "continuous", "bounds": [80.0, 250.0]},
        {"key": "pressure",    "type": "continuous", "bounds": [1.0, 15.0]},
        {"key": "catalyst",    "type": "categorical", "categories": ["Pd/C", "Pt/C", "Raney-Ni"]}
      ],
      "output_features": [
        {"key": "yield", "type": "continuous", "objective": "maximize"}
      ]
    },
    "strategy": {"strategy": "random", "n_candidates": 5}
  }'
```

---

## Multi-objective example — yield vs purity trade-off

When you have two or more outputs, BoFire returns a Pareto front.
Use `mobo` or `qparego` strategy (see [Tutorial 4](04_strategies.md)).

```bash
curl -s -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Yield-purity trade-off",
    "domain": {
      "name": "Polymer synthesis",
      "input_features": [
        {"key": "temperature", "type": "continuous",  "bounds": [50.0, 200.0]},
        {"key": "time",        "type": "continuous",  "bounds": [0.5, 8.0]},
        {"key": "solvent",     "type": "categorical", "categories": ["THF", "DCM", "EtOAc"]},
        {"key": "rpm",         "type": "discrete",    "values": [200, 400, 600]}
      ],
      "output_features": [
        {"key": "yield",  "type": "continuous", "objective": "maximize"},
        {"key": "purity", "type": "continuous", "objective": "maximize"}
      ]
    }
  }'
```

---

## Rules and constraints

| Rule | Detail |
|------|--------|
| At least 1 input feature | Required |
| At least 1 output feature | Required |
| `bounds` must have exactly 2 values | `[lower, upper]`, lower < upper |
| `categories` must be non-empty | Minimum 1 string |
| `discrete` values must be non-empty | Minimum 1 number |
| `mobo` / `qparego` require ≥ 2 outputs | Error returned otherwise |
| `sobo` requires exactly 1 output | Multi-output triggers error |
| Feature keys must be unique | Duplicate keys are rejected |

---

## Updating the strategy or context later

You do not have to specify a strategy at campaign creation time.
Add or replace it later:

```bash
CAMPAIGN_ID="<your-id>"

# Set strategy
curl -X PATCH http://localhost:8000/campaigns/$CAMPAIGN_ID/strategy \
  -H "Content-Type: application/json" \
  -d '{"strategy": "sobo", "n_candidates": 3}'

# Set context for LLM use
curl -X PATCH http://localhost:8000/campaigns/$CAMPAIGN_ID/context \
  -H "Content-Type: application/json" \
  -d '{"context": "Maximizing yield in a catalytic hydrogenation reaction."}'
```

---

## Next steps

- **[Tutorial 3 — Campaigns](03_campaigns.md)**: run the full optimization loop.
- **[Tutorial 4 — Strategies](04_strategies.md)**: pick the right strategy for your problem.
