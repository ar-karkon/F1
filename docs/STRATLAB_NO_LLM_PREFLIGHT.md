# F1-StratLab no-LLM — pinned source preflight and execution boundary

This document distinguishes a **verified code contract** from a
**completed machine-learning inference**.

Upstream (pinned in `third_party/F1-StratLab`):
- https://github.com/VforVitorio/F1-StratLab
- Commit: `b65c34e84c8a9d6e29f7a9741bbaa22b0aae851c`
- `src/strategy/inference/engine.py::run_lap(..., profile="no-llm")`
  dispatches to `src/strategy/inference/no_llm.py`.

Its `no-llm` mode avoids constructing LLM clients but **still executes
real ML networks** (pace XGBoost, tyre models including TCN, situation
LightGBM, race state and Monte Carlo). Upstream's own no-LLM tests are
deliberately marked `skip_no_tire_models`; its
`tests/conftest.py` requires
`data/models/tire_degradation/routing_config.json`. That file and the
related training artifacts are **not present in the public Git source**,
as described in upstream's data/model policy. Other needed input artifacts
include the featured-lap dataframe or `tests/fixtures/mini_race.parquet`.

To audit the real pinned checkout:

```bash
git submodule update --init third_party/F1-StratLab
python -m apex_f1.integrations.stratlab_preflight
```

CI `.github/workflows/upstream-integration.yml` now stores a machine-readable
`stratlab-no-llm-preflight` artifact. If the original trained model
artifacts are absent, the status is **BLOCKED_MISSING_MODELS_OR_FIXTURES**
and `runtime_executed = false`; it will NOT fabricate outputs or run a
dummy agent. To execute original inference, obtain weight files lawfully,
configure the separate upstream environment, and only then map its
`RaceState` and featured-lap inputs to a genuine chronological Apex
replay. The published OpenF1 as-of snapshot alone does not provide
all the upstream model features.

The SovInfra LLM API key is irrelevant to this specific no-LLM mode.
Do not substitute text LLM output for missing numeric model artifacts.
