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

## Verified real-data benchmark (20 November 2026)

**Reproducible GitHub Actions run:** [Multi-Race Chronological Calibration
Benchmark #44794792592](https://github.com/ar-karkon/F1/actions/runs/44794792592),
commit `204881cabfd140e212e5c122f03c618598bb1994`.
The run fetched real OpenF1 timing for all nine weekends, trained on
r1–3 only, fitted the one-parameter logit intercept on r4–5 only and
evaluated the frozen model on r6–9 only. The Actions artifact
`real-2024-multirace-calibration` contains the original aggregate JSON.

- **Base training:** 2,750 overlapping windows.
- **Calibration:** 1,728 overlapping windows with 244 positive out-lap windows
  (14.12%); fitted logit intercept **+0.23248553**.
- **Final holdouts:** **4,500** overlapping driver-lap windows across four
  different circuits; **322 positives** (**7.16%** observed). None of these
  outcomes was used to fit the baseline or calibrator.

### Pooled four-race scores (lower is better)

| Frozen method | Brier score | Log loss | 10-bin ECE |
| --- | ---: | ---: | ---: |
| Training-set constant base rate | **0.067674** | **0.264901** | **0.035198** |
| Uncalibrated pit-out v2 | 0.072806 | 0.279921 | 0.048244 |
| Intercept calibrated with r4–5 | 0.077231 | 0.292388 | 0.068889 |

**Validation result: FAILED TO BEAT THE SIMPLE BASELINE.** Both the raw
model and the calibrator generalize worse than the training-only event rate
on the four genuinely untouched test races, across all three scoring
measures. The intercept calibration **worsened** each metric.
This is a negative research result and is intentionally published.

### Per-race Brier score

| Unseen 2024 GP | Decision windows | Positive out-lap windows | Base rate | Raw model | Calibrated |
| --- | ---: | ---: | ---: | ---: | ---: |
| Miami (r6) | 1,022 | 83 | **0.075270** | 0.081315 | 0.085576 |
| Emilia-Romagna (r7) | 1,151 | 78 | **0.064695** | 0.069736 | 0.074284 |
| Monaco (r8) | 1,162 | 37 | **0.036440** | 0.045383 | 0.052700 |
| Canada (r9) | 1,165 | 124 | **0.095109** | 0.095727 | 0.097291 |

The earlier *single-race Japan test* (Brier 0.129186 raw vs 0.133608
base rate) was encouraging, but **not representative** of later races.
Japan was used for **calibration** in this new split and was not in the
final test. Calibration learned a higher out-lap prevalence from Japan
and China, then increased the base model log odds. Out-laps were much
less common on later held-out races, explaining the direction of failure.

**Interpretation:** The tested compound/tyre-age/race-stage bins do not
robustly beat a trivial historical prior for these events. The model
must remain explicitly labelled *research only / unvalidated*, and
this version must not be marketed as an accurate competitor prediction
or used to advise real pit-stop decisions.

**Next experiment (new untouched holdout required):** pre-register a
stronger conditional hazard model, improve track/race-normalized features
and flag red-flag/penalty out-laps; then evaluate on races not yet
consulted. Avoid repeatedly tuning to these four test races.



### API throttling in real-data experiments

OpenF1 returned HTTP 429 when importing nine race weekends rapidly on a
shared GitHub Actions runner. The client now honors numeric Retry-After,
uses bounded exponential backoff, and deliberately pauses between race
imports. Persistent rate limits are **errors**, never synthetic fallback
inputs. Full raw race laps are not uploaded or committed.
