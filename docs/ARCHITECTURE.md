# Architecture / Engineering decisions

## Current runtime

```text
Browser dashboard
      │  HTTP JSON
      ▼
FastAPI (src/apex_f1/api.py)
      │
      ▼
Toy paired Monte Carlo (src/apex_f1/simulator.py)
      │
      └── Reproducible seeded candidate-level results

Optional external path:
FastF1 historical API → fastf1_adapter.py → data/derived/*.json
                                   (not yet coupled to simulator)
```

- Local-only by default. No external credentials needed for the demo.
- No LLM calls, paid inference, live timing or external network requirements for the simulator.
- Pure-Python simulation makes deterministic numerical regression tests simple.
- The `/api/v1/` namespace makes future adapters and predictors separable.
- Model uses paired random samples for all strategies within one Monte Carlo trial.
- Dashboard is shipped as package data; deployed wheel and Docker both include the page.

## Intended modules (not implemented)

1. **Data contracts:** provenance, event/session ID, lap timestamp, feature flags, source permissions, tyre details and missing-value handling.
2. **Historical replay:** state at lap N must use only observations available by lap N.
3. **Tyre model:** time-split fitted degradation with compound, circuit, temperature, traffic and uncertainty.
4. **Opponent model:** pit timing hazard + historical behavioural features, with calibrated probabilities.
5. **Strategy layer:** safety car, weather, track position, pit traffic, undercut/overcut, compounds, tire allocation and 2026 regulatory changes.
6. **Agent layer:** retrieval and tool orchestration; model-free core decision algorithms must remain independently testable.
7. **User interface:** uncertainty bands, provenance, counterfactual explanations, human review and decision audit log.

## Non-goals of v0.1

No win or finishing-position probabilities, team-only data, 2026 race rules, full-car physics, AI training, or automatically executed racing decisions.

## Commercial readiness gates

See [VALIDATION.md](VALIDATION.md). Avoid promising accuracy, race performance or monetization before measured evidence.
