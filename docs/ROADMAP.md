# Roadmap — evidence before claims

## Phase 0 — repository foundation (present)

- [x] Independent MIT core, API, static UI and CLI.
- [x] Synthetic strategy engine with fixed-seed Monte Carlo.
- [x] CPU-only local workflow, tests, CI, Docker.
- [x] Historical FastF1 export utility.
- [x] Four upstream research repositories linked as pinned Git submodules, with licensing boundaries.
- [x] Initial remote GitHub CI successfully passed on Python 3.10 and 3.12.
- [x] TUM basic full-race kernel adapter in an isolated subprocess, with dedicated upstream CI.
- [x] F1-StratLab source-level run_lap contract verification (not yet executed).
- [x] Browser-based Integration Lab for source readiness and TUM reference race comparisons.
- [ ] Verify dedicated upstream CI run and stored JSON artifact.
- [ ] Execute F1-StratLab no-llm profile in its own isolated environment with historical data.
- [ ] Validate telemetry pipeline integration with adapter contract tests.

## Phase 1 — historic race replay

- [x] Implement normalized completed-lap history schema and unique (driver, lap) identifiers.
- [x] Provide FastF1 historical race import CLI (session R) into ignored local files.
- [x] Temporal cutoff based on earliest completed leader lap, with future-leak regression tests.
- [x] Add read-only historical replay API and local dashboard.
- [ ] Confirm live FastF1 2024 race fetch in dedicated GitHub Actions workflow.
- [ ] Extend import and validation to a diverse set of circuits, caution and wet-race scenarios.
- [ ] Robust missing laps and tyre compound normalization.
- [x] **Strict completed-lap chronology**: only records with end timestamp at or before cutoff; field-level real-time disclosure audit still pending.
- [x] Visualize a historical session separately from synthetic outputs.

**Gate:** deterministic session reconstruction and timestamp leakage tests.

## Phase 2 — learn tyre and pit models

- [ ] Train per-compound circuit-conditioned tyre performance with baselines.
- [ ] Infer pit loss from observed pit in/out records, not fixed constants.
- [ ] Calibrate uncertainty by circuit, weather and season.
- [ ] Introduce track-specific legality checks and 2026 regulation adapter.

**Gate:** performance improvement on unseen race weekends against simple heuristics.

## Phase 3 — opponent intelligence

- [ ] Pit timing hazard model with team/driver priors.
- [ ] Behavioural features: stint transitions, traffic response, safety-car response.
- [ ] Probability calibration (Brier score, reliability diagrams).
- [ ] Compare with historical/base-rate-only baselines.

**Gate:** consistently useful backtest out of sample and calibrated confidence.

## Phase 4 — strategy copilot

- [ ] Combine opponent priors and race simulator in counterfactual scenarios.
- [ ] Explanations must cite data timestamp, model version and uncertainty.
- [ ] Human approval; no automatic racing decisions.
- [ ] Optional LLM for explanation and tool calls (never source of numeric truth).
- [ ] Research-track pilot with small motorsport/sim-racing team.

**Gate:** blinded engineer feedback and evidence of decision-usefulness.

## Phase 5 — production feasibility

Data rights, circuit-specific modelling, access control, security, historical audit logs, uptime, latency and independent evaluation. No unverified performance marketing.
