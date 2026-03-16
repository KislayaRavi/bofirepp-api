# Tutorial 4 — Strategies

BoFire++ supports four optimization strategies. This tutorial explains what each one does, when to use it, and how to configure it.

---

## Strategy overview

| Strategy | Type | Prior data needed | Outputs supported | Best used when |
|----------|------|:-----------------:|:-----------------:|----------------|
| `random` | Sampling | No | Any | Cold start, baseline, debugging |
| `sobo` | Bayesian (single-obj) | Yes (≥ 1 obs) | Exactly 1 | One clear metric to optimize |
| `mobo` | Bayesian (multi-obj) | Yes (≥ 1 obs) | ≥ 2 | Multiple competing objectives |
| `qparego` | Bayesian (multi-obj) | Yes (≥ 1 obs) | ≥ 2 | Large candidate budgets, scalable |

---

## `random` — uniform random sampling

Draws candidates uniformly at random from the design space.
No model is fitted, no prior data is required.

**Use it to:**
- Explore the design space at the start of a campaign
- Generate a diverse initial dataset before switching to Bayesian
- Debug domain definitions quickly

```json
{"strategy": "random", "n_candidates": 10}
```

**Switching away:** once you have at least a few observations, switch to `sobo`, `mobo`, or `qparego` via `PATCH /campaigns/{id}/strategy`.

---

## `sobo` — Single-Objective Bayesian Optimization

Fits a Gaussian Process surrogate on your observations and uses Expected Improvement (EI) to suggest the next most promising candidate.

**Requirements:**
- At least 1 experiment observation
- Exactly 1 output feature

**Use it when** you have a single metric (e.g. maximize yield, minimize cost) and want the algorithm to intelligently balance exploration vs. exploitation.

```json
{"strategy": "sobo", "n_candidates": 3}
```

**Typical workflow:**

```
random (5–10 points)  →  switch to sobo  →  iterate until convergence
```

---

## `mobo` — Multi-Objective Bayesian Optimization (qEHVI)

Uses the q-Expected Hypervolume Improvement (qEHVI) acquisition function to build a Pareto front across multiple competing objectives simultaneously.

**Requirements:**
- At least 1 experiment observation
- At least 2 output features

**Use it when** you have trade-offs to navigate — e.g. maximize yield while also maximizing purity, or minimize cost while maximizing performance.

```json
{"strategy": "mobo", "n_candidates": 2}
```

The Pareto front in `proposals` gives you the set of non-dominated experiments to consider running next.

---

## `qparego` — qParEGO scalarization

An alternative multi-objective approach that scalarizes objectives using a random Chebyshev weight vector before applying single-objective BO.
Often faster than qEHVI for larger candidate batches.

**Requirements:** same as `mobo` (≥ 1 obs, ≥ 2 outputs)

**Use it when** `mobo` is too slow or you need larger batches of candidates.

```json
{"strategy": "qparego", "n_candidates": 5}
```

---

## Setting `n_candidates`

`n_candidates` controls how many experiment candidates are returned per proposal.

- Higher values → more parallelism in the lab (run several experiments at once)
- Lower values → faster iteration, each new result informs the next proposal sooner
- The value set on the strategy is used as the default; you can override it per-call:

```bash
curl -X POST http://localhost:8000/campaigns/$CID/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{"n_candidates": 8}'
```

---

## Switching strategies mid-campaign

You can change the strategy at any point without losing observations or proposals:

```bash
# Start with random
curl -X PATCH http://localhost:8000/campaigns/$CID/strategy \
  -H "Content-Type: application/json" \
  -d '{"strategy": "random", "n_candidates": 5}'

# … run some experiments, add observations …

# Switch to Bayesian
curl -X PATCH http://localhost:8000/campaigns/$CID/strategy \
  -H "Content-Type: application/json" \
  -d '{"strategy": "sobo", "n_candidates": 2}'
```

All prior proposals and observations are retained in `campaign.json`.

---

## Common errors and fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `422 — requires at least one experiment observation` | Bayesian strategy called with no data | Add observations first, or use `random` |
| `422 — mobo/qparego require ≥ 2 output features` | Domain has only 1 output | Add a second output, or switch to `sobo` |
| `503 — BoFire dependency not available` | PyTorch / BoFire not installed | `pip install ".[optimization]"` |

---

## Recommended starting recipe

```
1. Create campaign with "random", n_candidates = 8–12
2. Generate initial_proposal → run experiments → add observations
3. PATCH strategy to "sobo" (single output) or "mobo" (multiple outputs)
4. Generate proposal1 → run experiments → add observations
5. Repeat until you are satisfied with the results
```

---

## Next steps

- **[Tutorial 5 — LLM Integration](05_llm_integration.md)**: use Gemini to help interpret results.
