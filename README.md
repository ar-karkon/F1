# Apex Intelligence
### Explainable race strategy and opponent intelligence — open-source R&D

[![CI](https://github.com/ar-karkon/F1/actions/workflows/ci.yml/badge.svg)](https://github.com/ar-karkon/F1/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-research%20prototype-orange.svg)](docs/VALIDATION.md)

**Apex Intelligence** is an independent motorsport AI research project exploring race strategy, historical telemetry, opponent modelling, and human-in-the-loop decision support.

> **IMPORTANT:** The included strategy engine is a deliberately simple **SYNTHETIC, UNVALIDATED** Monte Carlo baseline with illustrative tyre wear and pace constants. It is not a real F1 strategy optimizer, makes no race-win predictions, and must not be used for real race operations.

## What's included now

- A deterministic, CPU-only Monte Carlo comparison of three counterfactual pit decisions.
- A responsive, interactive pit-wall research dashboard.
- A versioned FastAPI endpoint and OpenAPI docs at `/docs`.
- An optional historical FastF1 lap export (separate from the synthetic model).
- Pytest, Ruff CI on Python 3.10 and 3.12, Docker and local CLI.
- Four pinned upstream projects tracked as Git submodules under `third_party/`, plus licensing notes and evaluation standards.
- **Executable TUM basic race-time adapter** using original 2017 example parameters in an isolated subprocess (optional NumPy extra).
- **F1-StratLab source contract probe**, not a running agent integration.

## Quick start

Python 3.10+:

```bash
git clone https://github.com/ar-karkon/F1.git
cd F1
# Optional: populate pinned research projects under third_party/
git submodule update --init
python -m venv .venv
source .venv/bin/activate      # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
apex-f1 demo --trials 400
apex-f1 serve
```

Open **http://127.0.0.1:8000** for the strategy dashboard, **http://127.0.0.1:8000/integrations** for the TUM / StratLab research laboratory, or **http://127.0.0.1:8000/docs** for API docs. The TUM panel requires its checked-out submodule and `.[tum]` extra to execute.

Docker alternative:

```bash
docker build -t apex-f1 .
docker run --rm -p 8000:8000 apex-f1
```

Test:

```bash
ruff check src tests
pytest -q --ignore=tests/upstream
# With TUM+StratLab submodules checked out and `.[tum]` installed:
pytest -q tests/upstream
```

## API example

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/strategy/evaluate \
  -H "Content-Type: application/json" \
  -d '{"current_lap":28,"total_laps":57,"current_compound":"MEDIUM","current_tyre_age":16,"pit_loss_seconds":22,"safety_car_probability":0.15,"trials":400,"seed":7}'
```

Output includes expected **remaining seconds**, p10/p90 model bands, expected delta, and probability of being fastest **only among the modelled candidates**. This is not position, podium or victory probability.

## Research integration: execute the original TUM basic model

This integration calls the **original TUM source** at the pinned SHA, in a subprocess, using the **upstream 2017 Yas Marina sample parameters**. This demonstrates real source execution—not a modern F1 prediction. It is independent from the existing synthetic Monte Carlo model.

```bash
git submodule update --init third_party/race-simulation third_party/F1-StratLab
python -m pip install -e ".[dev,tum]"
apex-f1 integrations               # presence/contract checks (NOT runtime results)
apex-f1 tum-compare --pit-laps 18 25 32
```

Endpoint: `POST /api/v1/integrations/tum/compare` with `{"pit_laps":[18,25,32]}`. Requires the pinned submodule and NumPy; otherwise reports missing dependencies instead of faking results. A separate [upstream integration CI](.github/workflows/upstream-integration.yml) executes the actual kernel and publishes a comparison JSON artifact.

F1-StratLab is currently **contract-probed only**; no pretrained agent/models are run. See [integration progress](docs/INTEGRATION_PROGRESS.md).

## Optional: historical FastF1 data

```bash
python -m pip install -e ".[data]"
apex-f1 export-fastf1 --year 2024 --round 1 --session R --driver VER \
  --output data/derived/bahrain-2024-ver.json
```

Exports historical timing, compound, tyre life, and stints. This **does not** train the simulator automatically or claim access to real-time F1 team telemetry. Respect upstream API terms and source data usage rights.

## Included upstream research projects (Git submodules)

Four open-source projects are **tracked in this repository as pinned Git submodules** under [third_party/](third_party). GitHub shows links to each external repository at the precise commit recorded by F1; the actual external source is downloaded on checkout, **not copied into F1 Git history**.

```bash
# After cloning the repo:
git submodule update --init
# Or do it in one command on a fresh clone:
git clone --recurse-submodules https://github.com/ar-karkon/F1.git

# Compatibility wrapper:
bash scripts/clone_upstreams.sh
```

Submodules: TUM Race Simulation (LGPL-3.0), F1-StratLab (Apache-2.0), Pit Wall Engineer (MIT) and Motorsport Analytics Pipeline (MIT). Upstream projects are **not yet installed, executed or integrated with the MVP**. Source modifications require working on a fork or deliberately migrating selected code through a license-reviewed subtree. See [repository layout](docs/REPOSITORY_STRATEGY.md) and [upstream inventory](docs/UPSTREAM_PROJECTS.md).

## Project map

```text
src/apex_f1/
  api.py                  FastAPI service and dashboard
  simulator.py            Synthetic paired Monte Carlo baseline
  fastf1_adapter.py       Optional real historical lap exporter
  integrations/           Pinned TUM worker and F1-StratLab contract probe
  cli.py                  Local commands
  static/index.html       Interactive strategy dashboard
tests/                    Simulation and API regression tests
third_party/              Four pinned upstream research submodules (optional checkouts)
docs/
  ARCHITECTURE.md         Data flow and integration interfaces
  ROADMAP.md              Prioritized build plan
  VALIDATION.md           Validation gates and model limitations
  UPSTREAM_PROJECTS.md    Upstream integration and licensing notes
scripts/clone_upstreams.sh Helper to check out pinned submodules
```

## Why this architecture?

Start with a transparent, testable baseline; then replace each toy assumption with a validated component. Our intended differentiator is **opponent decision modelling with calibrated uncertainty**, not a generic chat interface or unsupported "AI predicts race wins" claim.

The 2026 F1 regulations, especially energy usage, overtaking and active aerodynamic modes, require additional modelling before any 2026-specific race claims.

## Contributing and research scope

Open issues should identify the actual dataset, evaluation split, reference baseline, acceptance criteria and license constraints. Never commit private team telemetry, access tokens, or data that may not be redistributed.

- [Architecture](docs/ARCHITECTURE.md)
- [Development roadmap](docs/ROADMAP.md)
- [Validation and scientific integrity](docs/VALIDATION.md)
- [External open-source projects](docs/UPSTREAM_PROJECTS.md)
- [Integration progress and limits](docs/INTEGRATION_PROGRESS.md)

**License:** MIT for code authored in this repository; upstream packages and datasets retain their own terms. No affiliation with Formula 1 or any team is implied.
