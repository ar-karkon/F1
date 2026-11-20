"""Offline, deterministic multi-race calibration and no-leakage checks."""
from __future__ import annotations

from dataclasses import replace

import pytest

from apex_f1.calibration import (
    InterceptCalibrator,
    evaluate_races,
    fit_calibrator,
)
from apex_f1.opponent import train_pit_model
from apex_f1.replay import CompletedLap, HistoricalRace


def fixture_race(round_number: int) -> HistoricalRace:
    """Clearly synthetic test fixture, never real historical benchmark data."""
    records = []
    for driver in range(10):
        # Alter event prevalence across racing weekends to stress calibration.
        stops = {12 + driver % 4, 26 + driver % 3}
        if round_number >= 4 and driver % 2 == 0:
            stops.add(36 + driver % 2)
        for lap in range(1, 43):
            records.append(CompletedLap(
                driver=f"F{driver:02}",
                lap_number=lap,
                end_session_seconds=lap * 100 + driver,
                lap_seconds=100.0,
                compound="MEDIUM" if lap < 16 else "HARD",
                tyre_life=(lap % 16) + 1,
                pit_out=lap in stops,
            ))
    return HistoricalRace(2024, round_number, records)


def fitted_pair():
    baseline = train_pit_model([fixture_race(x) for x in (1, 2, 3)])
    calibrator = fit_calibrator(baseline, [fixture_race(4), fixture_race(5)])
    return baseline, calibrator


def test_calibration_is_deterministic_and_temporally_separated():
    a, b = fitted_pair()
    assert len(b.model_fingerprint) == 64
    assert b.calibration_races == ["2024:4:R", "2024:5:R"]
    assert b.model_training_races == a.training_races
    assert b.calibration_windows > 100
    assert 0 < b.calibration_positive < b.calibration_windows
    assert -3 <= b.intercept <= 3
    assert 0 < b.apply(0.2) < 1
    assert b == fit_calibrator(a, [fixture_race(4), fixture_race(5)])


def test_test_races_are_completely_held_out():
    a, b = fitted_pair()
    with pytest.raises(ValueError, match="AFTER calibration"):
        evaluate_races(a, b, [fixture_race(5), fixture_race(6)])
    with pytest.raises(ValueError, match="later than training"):
        fit_calibrator(a, [fixture_race(2), fixture_race(4)])
    with pytest.raises(ValueError, match="Duplicate"):
        fit_calibrator(a, [fixture_race(4), fixture_race(4)])


def test_model_fingerprint_prevents_accidental_calibration_reuse():
    a, b = fitted_pair()
    modified = replace(a, event_count=a.event_count + 1)
    with pytest.raises(ValueError, match="different base model"):
        evaluate_races(modified, b, [fixture_race(6), fixture_race(7)])


def test_multirace_report_contains_pooled_brier_ece_and_logloss():
    a, b = fitted_pair()
    output = evaluate_races(a, b, [fixture_race(x) for x in (6, 7, 8, 9)])
    assert output["train_races"] == ["2024:1:R", "2024:2:R", "2024:3:R"]
    assert output["calibration_races"] == ["2024:4:R", "2024:5:R"]
    assert output["test_races"] == [f"2024:{x}:R" for x in (6, 7, 8, 9)]
    pooled = output["pooled"]
    assert pooled["decision_windows"] == sum(
        r["metrics"]["decision_windows"] for r in output["per_race"]
    )
    assert pooled["positive_windows"] > 0
    assert set(pooled["brier"]) == {"base", "raw", "calibrated"}
    assert set(pooled["log_loss"]) == {"base", "raw", "calibrated"}
    assert set(pooled["expected_calibration_error_10_bins"]) == {
        "base", "raw", "calibrated"
    }
    for k in ("base", "raw", "calibrated"):
        assert 0 <= pooled["brier"][k] <= 1
        assert pooled["log_loss"][k] >= 0
        assert sum(
            entry["count"] for entry in pooled["reliability_bins"][k]
        ) == pooled["decision_windows"]


def test_calibrator_file_round_trip(tmp_path):
    a, b = fitted_pair()
    path = b.save(tmp_path / "calibration.json")
    restored = InterceptCalibrator.load(path)
    assert restored == b
    assert evaluate_races(a, restored, [fixture_race(6), fixture_race(7)]) == (
        evaluate_races(a, b, [fixture_race(6), fixture_race(7)])
    )


def test_holdout_labels_cannot_change_calibration_or_model():
    model, cal = fitted_pair()
    target = fixture_race(6)
    changed = []
    for row in target.laps:
        changed.append(
            replace(row, pit_out=not row.pit_out) if row.lap_number > 25 else row
        )
    _ = evaluate_races(model, cal, [target, fixture_race(7)])
    other = evaluate_races(
        model, cal, [HistoricalRace(2024, 6, changed), fixture_race(7)]
    )
    assert cal == fit_calibrator(model, [fixture_race(4), fixture_race(5)])
    assert other["calibration_intercept"] == cal.intercept
    assert other["per_race"][0]["metrics"]["brier"] != (
        evaluate_races(model, cal, [target, fixture_race(7)])["per_race"][0]["metrics"]["brier"]
    )


def test_earliest_test_must_come_after_latest_calibration():
    a, b = fitted_pair()
    with pytest.raises(ValueError, match="AFTER calibration"):
        b.ensure_test(a, fixture_race(4))
