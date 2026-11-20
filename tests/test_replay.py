"""Regression tests against temporal leakage, not predictive accuracy."""
from __future__ import annotations

import json

import pytest

from apex_f1.replay import CompletedLap, HistoricalRace


def rows():
    return [
        CompletedLap("AAA", 1, 90, 90, "SOFT", 1, 1, 1),
        CompletedLap("BBB", 1, 92, 92, "MEDIUM", 1, 1, 2),
        CompletedLap("AAA", 2, 180, 90, "SOFT", 2, 1, 1),
        CompletedLap("BBB", 2, 185, 93, "MEDIUM", 2, 1, 2, pit_in=True),
        CompletedLap("AAA", 3, 270, 90, "SOFT", 3, 1, 1),
        CompletedLap("BBB", 3, 280, 95, "HARD", 1, 2, 2, pit_out=True),
    ]


def test_cutoff_excludes_slower_car_same_numbered_lap():
    history = HistoricalRace(2024, 1, rows())
    result = history.snapshot(2)
    bbb = next(row for row in result["drivers"] if row["driver"] == "BBB")
    assert result["cutoff_session_seconds"] == 180
    assert bbb["last_completed_lap"] == 1
    assert bbb["last_known_compound"] == "MEDIUM"
    assert bbb["observed_pit_ins"] == 0
    assert result["n_completed_records_visible"] == 3


def test_snapshot_unaffected_by_any_post_cutoff_changes():
    base = HistoricalRace(2024, 1, rows()).snapshot(2)
    changed = rows()
    changed[3] = CompletedLap("BBB", 2, 185, 93, "WET", 2, 1, 2, pit_in=False)
    changed[4] = CompletedLap("AAA", 3, 270, 90, "HARD", 3, 1, 1)
    assert HistoricalRace(2024, 1, changed).snapshot(2) == base


def test_snapshot_does_not_include_drivers_not_yet_observed():
    r = rows() + [CompletedLap("CCC", 3, 281, 89, "HARD", 1, 1, 3)]
    state = HistoricalRace(2024, 1, r).snapshot(2)
    assert {driver["driver"] for driver in state["drivers"]} == {"AAA", "BBB"}


def test_boundaries_monotonic():
    out = HistoricalRace(2024, 1, rows()).boundaries()
    assert [row["lap"] for row in out] == [1, 2, 3]
    assert [row["session_seconds"] for row in out] == [90, 180, 270]


def test_pit_events_become_visible_only_when_lap_completed():
    history = HistoricalRace(2024, 1, rows())
    assert next(x for x in history.snapshot(2)["drivers"] if x["driver"] == "BBB")[
        "observed_pit_ins"
    ] == 0
    assert next(x for x in history.snapshot(3)["drivers"] if x["driver"] == "BBB")[
        "observed_pit_ins"
    ] == 1


def test_roundtrip(tmp_path):
    race = HistoricalRace(2024, 1, rows())
    path = tmp_path / "race.json"
    race.save(path)
    restored = HistoricalRace.load(path)
    assert restored.to_json() == race.to_json()
    assert json.loads(path.read_text())["schema_version"] == 1


def test_rejects_future_schema():
    with pytest.raises(ValueError, match="schema"):
        HistoricalRace.from_json({"schema_version": 99})


def test_reject_duplicate_laps():
    with pytest.raises(ValueError, match="Duplicate"):
        HistoricalRace(2024, 1, rows() + [rows()[0]])


def test_missing_lap_unavailable():
    with pytest.raises(ValueError, match="No leader"):
        HistoricalRace(2024, 1, rows()).snapshot(9)


def test_summary_is_separate_from_prediction_snapshot():
    race = HistoricalRace(2024, 1, rows())
    assert race.summary()["has_predictions"] is False
    assert "available_leader_laps" not in race.snapshot(1)
