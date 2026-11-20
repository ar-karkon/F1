# Chronological multi-race calibration (research baseline)

This benchmark evaluates whether a **frozen post-hoc logit-intercept
calibration** improves a pit-exit proxy forecast on *four unseen races*.
It does not make the pit-window model safe for live strategy. The original
empirical model (`pit-window-outlap-v2`) is not re-trained on evaluation data.

## Fixed research split

| Purpose | F1 2024 Grand Prix rounds |
| --- | --- |
| Base training | 1 Bahrain, 2 Saudi Arabia, 3 Australia |
| Intercept calibration | 4 Japan, 5 China |
| Unseen final tests | 6 Miami, 7 Emilia-Romagna, 8 Monaco, 9 Canada |

OpenF1 historical data is imported locally, and **only aggregate
derived results** are uploaded to GitHub Actions. No SovInfra or other LLM
is called. The historical OpenF1 source requires non-commercial usage and
separate data rights for commercial deployments.

### Model and calibration method

- Target: OpenF1 `is_pit_out_lap` in the **next 3 consecutive driver
  completed laps**, excluding race lap 1. This is an *out-lap proxy*,
  not confirmation of a strategic tyre-change pit stop.
- Base model: hierarchical smoothed empirical compound+tyre-age+race-stage
  bin frequencies fit on rounds 1–3 only.
- Calibrator: a **single intercept** added to the base model log odds
  (not temperature scaling / isotonic). Fit on rounds 4–5 only, with
  fixed L2 penalty strength 20 and maximum adjustment ±3. This attempts
  base-rate shift correction without overfitting a flexible mapping.
- Test: reports Brier (lower better), log loss (lower better) and 10-bin
  expected calibration error (ECE; lower better), per race and pooled.
  It compares calibrated model, uncalibrated model and **training-only
  global event-rate** baseline. If calibration worsens results, report
  that explicitly. Never adjust the intercept on the test races.
- Race files must be chronologically ordered and distinct. A SHA-256
  fingerprint binds the calibrator to the exact trained baseline file;
  inconsistent and future-trained models are rejected.

### Reproduction

```bash
python -m pip install -e ".[dev]"
for round in 1 2 3 4 5 6 7 8 9; do
  apex-f1 import-race --year 2024 --round "$round" --provider openf1
done
apex-f1 fit-pit-model --train 2024:1 2024:2 2024:3 --horizon 3
apex-f1 fit-pit-calibrator --calibrate 2024:4 2024:5
apex-f1 evaluate-pit-multi --test 2024:6 2024:7 2024:8 2024:9
```

The model/calibrator live only in gitignored `data/derived/`, not the
repository. The [Actions workflow](../.github/workflows/multirace-calibration.yml)
runs the entire import and uploads a short JSON report.

### Statistical limitations

- These are correlated **overlapping driver-lap windows**, not
  independently sampled bets or complete races.
- The four held-out races share a year and regulations; a future-season
  domain shift remains untested.
- ECE uses coarse fixed 10 bins; small bin counts do not justify
  strong reliability claims.
- Historical tyre ages, compound assignments and pit-out flags may
  reflect post-processing; they are not guaranteed to be live-available.
- Pit-out can reflect penalties, red-flag resumption or pit-lane starts.
- No accuracy claims about stop intent, race outcomes, win probability,
  professional race strategy or financial return are supported.

**Evidence status:** the actual workflow run and measured results will
be linked below after real execution. If it fails, no fabricated scores
are acceptable.
