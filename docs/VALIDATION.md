# Scientific integrity and validation plan

## Present limitations

The `simulator.py` engine is a minimal illustrative model. Tyre pace and degradation are hardcoded, lap noise is Gaussian, safety car is represented by a single sampled event, and the only pit effect is a simplified time cost. It omits opponent traffic, rain, crashes, mechanical issues, tyre allocation, compulsory compound rules, pit windows, track layout, and the 2026 rule set.

**Never use v0.1 for racing operations, driver safety decisions, betting, or commercial accuracy claims.**

`probability_fastest_of_candidates` means the fraction of simulated trials where that option is fastest **among only three defined options**. It is NOT the probability of winning, finishing ahead of an opponent, making a podium, or predicting real F1 strategy.

## Required out-of-sample validation

1. Register data sources, versions, session, timestamps and permissible usage.
2. Train on earlier races, validate on later races, test on holdout weekends.
3. At lap N, remove any data generated after lap N including final finish result.
4. Compare against: stay out, fixed pit heuristics, simple degradation regression.
5. Measure time-error distributions, strategy regret against counterfactual assumptions, calibration and inference time.
6. Report sample size, missingness, confidence intervals and failure cases.
7. Test especially wet races, cautions, penalties, atypical compounds and unseen circuits.
8. Re-evaluate after 2026 regulation changes; avoid transferring old behavior without qualification.
9. Evaluate for team/race ethics, human-in-the-loop operations and legal data rights.

## Avoid misleading benchmarks

Observed historical finishing position is not a valid causal label for an alternative pit strategy. A counterfactual can only be assessed under an explicit simulator and its uncertainty. Show both offline fit and simulation assumptions. Do not equate generated simulation metrics with real race advantage.

## Exit criteria for any external pilot

- Real historical sessions replayed without timestamp leakage.
- Documented circuit and regulation scope.
- Accuracy and calibration improvements shown vs transparent baselines.
- External validation and clearly communicated confidence limits.
- No confidential telemetry or copyrighted upstream data redistributed without rights.

## Measured 2024 pit-out baseline — negative generalization result

The chronological nine-race study (r1–3 train, r4–5 calibrate, r6–9
final test) executed successfully using real OpenF1 historical data:
[GitHub Actions run #44794792592](https://github.com/ar-karkon/F1/actions/runs/44794792592).

On 4,500 overlapping, non-independent driver-lap windows from four
untouched races, the held-out Brier scores were **0.067674** for a
constant training-set base rate, **0.072806** for the fitted empirical
pit-out model, and **0.077231** after one-parameter calibration.
Log loss and ECE also worsened. The real test shows that this
feature is currently **not validated to outperform a trivial prior**.
See [full metrics](MULTIRACE_CALIBRATION.md). The previous positive
single-race Japan score is not an appropriate overall accuracy claim.
