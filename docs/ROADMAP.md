# Roadmap — evidence before claims

## Phase 0 — repository foundation (present)

- [x] Independent MIT core, API, static UI and CLI.
- [x] Synthetic strategy engine with fixed-seed Monte Carlo.
- [x] CPU-only local workflow, tests, CI, Docker.
- [x] Historical FastF1 export utility.
- [x] Third-party references with licensing boundaries.
- [ ] Verify remote CI results after initial push.

## Phase 1 — historic race replay

- [ ] Define real `RaceSnapshot` data contract and event identifiers.
- [ ] Import a set of historical races through FastF1 with cache and provenance.
- [ ] Robust missing laps and tyre compound normalization.
- [ ] **Strict chronological replay**: only information at decision time.
- [ ] Visualize a historical session separately from synthetic outputs.

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
