# Pit-window research benchmark: Japan GP 2024

**Executed on GitHub Actions, 2026-11-20**
- Workflow: https://github.com/ar-karkon/F1/actions/runs/44776941827
- Code commit: `5d1e12febde9a40a0ce012674787ad5e38a6393b`
- Model version: `pit-window-outlap-v2`
- Data source: OpenF1 *historical* research API (not an official feed)
- Target: OpenF1 `laps.is_pit_out_lap` in the NEXT THREE driver-completed laps,
  excluding race lap 1. Not an observed pit-entry or confirmed tyre change.

## Chronological split

| Purpose | Events |
|---|---|
| Training | 2024 Bahrain (round 1), Saudi Arabia (round 2), Australia (round 3) |
| Holdout | 2024 Japan (round 4) |
| Features | Completed lap number, last-observed tyre compound, last-observed tyre age |
| Train decision windows | 2,750 (292 positive) |
| Japan decision windows | 798 (124 positive; 15.54%) |
| Training-only overall event rate | 10.68% |

No data from Japan 2024 was used for model fitting. The baseline
uses **hierarchical smoothed bin frequencies**, not an LLM prediction or
a learned team-specific strategy.

## Out-of-sample results

| Brier score (lower is better) | Result |
|---|---:|
| Pit-window empirical v2 | **0.129186** |
| Training-only global base rate | 0.133608 |
| Absolute improvement | 0.004422 |

**Interpretation:** modest improvement over a simple training base-rate
on this *single* held-out race. Do not represent this as a calibrated,
professional-grade model or as evidence of race outcome improvement.

### Calibration warning

| Predicted band | Windows | Mean forecast | Observed out-lap rate |
|---|---:|---:|---:|
| 0–20% | 690 | 8.11% | 15.22% |
| 20–40% | 102 | 24.00% | 13.73% |
| 40–60% | 6 | 43.44% | 83.33% |

This shows **substantial calibration mismatch**, especially in the low
and medium bins. The last band has only six examples. No rigorous
statistical uncertainty or multiple-circuit test has yet been performed.
Per-lap windows overlap; they are not independent observations.

## Data quality issue caught and fixed

The first version attempted to align OpenF1 `pit` events by identical
`lap_number` and compare the pit event timestamp to that lap's recorded
completion. It incorrectly preserved only 18 of 54 Japanese pit events,
yielding zero positive examples in the original holdout benchmark.
**Those first benchmark numbers were invalid and are superseded.**

The updated importer assigns pit event timestamps to the first driver
lap that actually completed after the event timestamp. A subsequent
diagnostic found:

- Raw `pit` events: **54**
- Imported timestamp-safe pit event flags: **54**
- OpenF1 `is_pit_out_lap` flags: **54**

The pit-window model uses **pit-out flags**, not the pit-entry flags, as
its target for clearer, testable semantics. Pit-out flags can occur on
red-flag restarts, pit-lane starts or drive-throughs, so the v2 target
still requires filtering and domain validation.

## Reproduction

```bash
python -m pip install -e ".[dev]"
for round in 1 2 3 4; do
  apex-f1 import-race --year 2024 --round "$round" --provider openf1
done
apex-f1 fit-pit-model --train 2024:1 2024:2 2024:3 --horizon 3
apex-f1 backtest-pit --year 2024 --round 4
apex-f1 predict-pit --year 2024 --round 4 --lap 20
```

Outputs are read from ignored local files. Only the **aggregate derived
benchmark JSON** is uploaded as a GitHub Actions artifact; full historical
timing datasets and fitted model files are not published by the workflow.

## What would make this pitch-ready?

1. Multiple year/circuit chronological holdouts with calibration reports.
2. Clear filtering of safety-car/red-flag/pit lane starts and drive-throughs.
3. Time-to-event survival/hazard benchmark against stronger trivial baselines.
4. Field-level real-time disclosure/latency tests and rights-cleared data.
5. Isolated F1-StratLab no-LLM run under issue #7, evaluated separately.

No win probability, pit-strategy optimization, team-specific telemetry,
monetary benefit or commercial data rights are claimed.
