# Opponent Pit Window v1 — empirical, reproducible, historical baseline

## Research question

Given the **last completed lap** of a driver, estimate the empirical
likelihood that an OpenF1 `pit` event is recorded within the **next three
completed driver laps**. This is an event-frequency baseline, NOT:
- a prediction of a rival's intentions, race position or race victory,
- a recommended stop lap, or
- evidence of performance versus professional team strategy models.

The output is not from SovInfra/LLMs. SovInfra, when enabled separately,
continues to explain observations, never calculate numerical pit probabilities.

## What is the model?

`src/apex_f1/opponent.py` keeps an empirical table of binary pit event
outcomes, binned by:
- last observed compound: SOFT, MEDIUM, HARD, INTERMEDIATE, WET, UNKNOWN;
- last observed tyre age: unknown, 0–9, 10–19, 20–29, 30+;
- observed driver completed-lap number: early (<20), middle (20–39), late (40+).

The H=3 outcome is **1** if the driver's next H consecutive completed
laps contain at least one pit-in record, otherwise **0**. Tail windows with
fewer than H consecutive future completed laps (retired cars, race end,
missing lap data) are **excluded** from training and evaluation rather than
incorrectly labelled zero.

The overall historic event rate is smoothed with 2 pseudopositives in
4 examples; coarse compound+age rates shrink to this with strength 30;
compound+age+stage rates shrink to coarse rates with strength 40.
These are *fixed parameters*, not hyperparameters tuned on the holdout.
No track, driver or team identities are encoded.

## Grounding and no-leakage

Features for a lap snapshot come only from the last already-completed lap
for each driver as of the selected leader lap timestamp. **The future
pit-event labels are consulted only in previously completed training races
or for scoring a separate held-out historical race**, never as prediction
features. No last-race outcome, championship standings or future position
data enters the features. Training on the evaluation race is refused, and
training races must chronologically precede it.

Data source issue: OpenF1 historical `date_start` is approximate and
historic position/tyre values may have been revised after an event.
Filtering by as-of lap completion mitigates row-level lookahead but cannot
guarantee a true live field publication timestamp. Therefore probabilities
are not valid for operational racing without a new data agreement and audit.

### Train and verify the actual historical baseline

```bash
python -m pip install -e ".[dev]"

for round in 1 2 3; do
  apex-f1 import-race --year 2024 --round "$round" --provider openf1
done
apex-f1 import-race --year 2024 --round 4 --provider openf1

apex-f1 fit-pit-model --train 2024:1 2024:2 2024:3 --horizon 3
apex-f1 backtest-pit --year 2024 --round 4
apex-f1 predict-pit --year 2024 --round 4 --lap 20
apex-f1 serve
```

Open `http://localhost:8000/replay`. A local model is read from the
gitignored `data/derived/pit-window-model.json`; raw training race files
stay in gitignored `data/derived/`. API GET:
- `/api/v1/opponent/status`: whether a local baseline was fitted.
- `/api/v1/historical/2024/4/opponent-pit/20`: point-in-time pit frequencies.

No API call performs training or downloads a new race. When the model is
missing, API reports that explicitly. Predictions for a training race are
refused with an explicit 422 error.

## Out-of-sample validation

The optional `.github/workflows/pit-window-benchmark.yml` imports 2024
Bahrain/Saudi Arabia/Australia *training races*, then **2024 Japan as
holdout**, computes the Brier score against the **training-set global event
rate**, and uploads only aggregate benchmark results as an artifact.

Metrics: train example count, total pit-positive windows, held-out decision
windows, observed positive rate, Brier score for our empirical model vs the
training-only base-rate model (lower is better), and fixed-bin calibration
counts. These windows overlap temporally, so 1,000 windows do not equal
1,000 independent experimental trials. A single held-out race cannot
establish generalization, especially for future regulation changes.

If Brier is *worse* than the base rate, report this clearly. Do not
present the baseline as profitable, accurate or suitable for a racing team
without multiple time-held-out circuit/year benchmarks and data rights.

## Next gate

1. Verify historical pit event alignment on full race footage/timing.
2. Run multiple held-out weekends and circuits, stratify weather/SC regimes.
3. Fit a calibrated hazard/survival model and competing trivial baselines.
4. Test F1-StratLab's separate `no-llm` runtime (GitHub issue #7).
5. Integrate explicit counterfactual simulation only when validated, not
   by asking an LLM to invent pit time savings.
