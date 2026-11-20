# Upstream integration progress

## TUM Race Simulation — experimental executable adapter

TUM basic full-race kernel: `racesim_basic/src/calc_racetimes_basic.py::calc_racetimes_basic` at pinned commit `96ef2c2`.

**Integrated via an isolated subprocess.** The worker dynamically loads the original source from the tracked submodule rather than copying it into our MIT-licensed core. This avoids importing the entire historical package and its old TF 2.2/CVXPY dependency chain.

Input parameters: upstream `pars_YasMarina_2017.ini`, an *illustrative 2017* one-driver, open-track race model. The integration compares candidate **full-race** pit inlap indices from a single starting compound to a new compound. It does NOT use our synthetic Monte Carlo simulator, and the two outputs must not be conflated.

Run:

```bash
git submodule update --init third_party/race-simulation
python -m pip install -e ".[dev,tum]"
apex-f1 tum-compare --pit-laps 18 25 32
```

REST: `POST /api/v1/integrations/tum/compare` with `{"pit_laps":[18,25,32],"start_compound":"A4","next_compound":"A3"}`. The default `GET /api/v1/integrations/status` checks source presence. Fallback if not checked out: HTTP 503, not fabricated results.

Validation: `.github/workflows/upstream-integration.yml` checks out actual pinned source and executes the **real** TUM basic model, with source contract and deterministic response tests. On successful CI it also stores a JSON artifact.

### Limits

TUM LGPL-3.0 source remains upstream. Exact attribution and version are recorded in output. Input parameters are NOT fitted to today's teams/tracks; no traffic model, current rules, 2026 energy management, opponent behaviour or win probability is inferred. **This is a functioning research integration, not a race-ready optimizer.**

## F1-StratLab — source contract compatibility probe only

`stratlab.probe_stratlab` parses `src/strategy/inference/engine.py` as an AST to confirm that `run_lap(race_state, laps_df, *, profile=...)` is exported at its pinned revision.

The source needs Python >=3.10 and <3.13, real featured laps data, model artifacts and a large ML/NLP dependency stack. We intentionally do **not** install its complete environment in the Apex core or claim that its agents have been executed.

Next milestone: run its `no-llm` profile in an isolated environment on one legitimate historical race and map `RaceState`, `laps_df`, outputs and model version to an explicit Apex adapter. Its labels, model outputs and recommendations must be validated on held-out races before being shown as real predictions.

## Reproducibility and provenance

`APEX_F1_UPSTREAM_DIR` can override the checkout root for wheel or external deployment. Submodule SHAs are pinned in the parent Git commit. Upstream binaries or training artifacts are not republished.
