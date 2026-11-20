"""Opponent pit-window baseline tests. No remote API calls or confidential telemetry."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apex_f1.api import app
from apex_f1.historical_import import race_file
from apex_f1.opponent import PitModel, train_pit_model
from apex_f1.replay import CompletedLap, HistoricalRace

client = TestClient(app)


def sample_race(year: int, round_number: int, *, driver_count: int = 8) -> HistoricalRace:
    """Illustrative fixtures explicitly NOT presented as real historical laps."""
    rows = []
    for k in range(driver_count):
        driver = f"T{k:02}"
        for lap in range(1, 34):
            pit = lap in {12 + (k % 4), 25 + (k % 3)}
            rows.append(
                CompletedLap(
                    driver=driver,
                    lap_number=lap,
                    end_session_seconds=lap * 100 + k,
                    lap_seconds=100,
                    compound="MEDIUM" if lap < 15 else "HARD",
                    tyre_life=(lap % 16) + 1,
                    stint=1 if lap < 15 else 2,
                    position=k + 1,
                    pit_out=pit,
                )
            )
    return HistoricalRace(year, round_number, rows)


def fitted_model() -> PitModel:
    races = [sample_race(2023, index) for index in (1, 2, 3)]
    return train_pit_model(races)


def test_training_is_deterministic_and_survival_labels_counted():
    model = fitted_model()
    other = fitted_model()
    assert model == other
    assert model.example_count >= 100
    assert 0 < model.event_count < model.example_count
    assert model.training_races == ["2023:1:R", "2023:2:R", "2023:3:R"]


def test_holdout_prediction_has_consistent_probabilities():
    model = fitted_model()
    race = sample_race(2024, 1)
    predicted = model.predict_snapshot(race.snapshot(17))
    assert predicted["holdout_race"] == "2024:1:R"
    assert predicted["mode"] == "HISTORICAL_EMPIRICAL_PIT_WINDOW_BASELINE"
    assert len(predicted["predictions"]) == 8
    assert all(
        0 < item["pit_within_next_n_driver_laps_probability"] < 1
        for item in predicted["predictions"]
    )
    assert predicted["training_races"] == model.training_races


def test_predictions_stable_when_future_holdout_laps_change():
    model = fitted_model()
    target = sample_race(2024, 1)
    state = target.snapshot(17)
    first = model.predict_snapshot(state)
    altered = [
        CompletedLap(
            driver=row.driver,
            lap_number=row.lap_number,
            end_session_seconds=row.end_session_seconds,
            lap_seconds=row.lap_seconds,
            compound="WET" if row.lap_number > 17 else row.compound,
            tyre_life=0 if row.lap_number > 17 else row.tyre_life,
            stint=row.stint,
            position=row.position,
            pit_in=row.pit_in,
            pit_out=True if row.lap_number > 17 else row.pit_out,
        )
        for row in target.laps
    ]
    second = model.predict_snapshot(HistoricalRace(2024, 1, altered).snapshot(17))
    assert first == second


def test_censored_tail_does_not_count_as_no_pit():
    race = sample_race(2023, 1, driver_count=5)
    model = train_pit_model([race])
    # For H=3, all driver observations on laps 31-33 are censored.
    # Pit-in observation rows are excluded.
    assert model.example_count == 5 * (33 - 3 - 2)
    # Explicit test of smaller chronological future sequence:
    from apex_f1.opponent import _examples

    target = HistoricalRace(2024, 1, [
        CompletedLap("ABC", lap, 100 * lap, pit_out=lap == 3)
        for lap in range(1, 6)
    ])
    labels = [(row.lap_number, label) for row, label in _examples(target, 3)]
    assert labels == [(1, 1), (2, 1)]


def test_in_sample_race_rejected():
    model = fitted_model()
    with pytest.raises(ValueError, match="In-sample"):
        model.predict_snapshot(sample_race(2023, 2).snapshot(15))
    with pytest.raises(ValueError, match="In-sample"):
        model.backtest(sample_race(2023, 2))


def test_backtest_on_unseen_race_produces_brier_and_calibration():
    report = fitted_model().backtest(sample_race(2024, 1))
    assert report["mode"] == "HISTORICAL_OUT_OF_SAMPLE_BACKTEST"
    assert report["n_decision_windows"] >= 100
    assert report["n_positive_windows"] > 0
    assert 0 <= report["brier_model"] <= 1
    assert 0 <= report["brier_base_rate"] <= 1
    assert sum(row["count"] for row in report["calibration_bins"]) == report[
        "n_decision_windows"
    ]


def test_serialize_roundtrip(tmp_path):
    model = fitted_model()
    restored = PitModel.load(model.save(tmp_path / "pit.json"))
    assert restored == model
    assert restored.backtest(sample_race(2024, 1)) == model.backtest(sample_race(2024, 1))


def test_duplicate_training_race_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        train_pit_model([sample_race(2023, 1), sample_race(2023, 1)])


def test_no_model_endpoint_explains_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("F1_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APEX_PIT_MODEL_FILE", str(tmp_path / "pit.json"))
    response = client.get("/api/v1/opponent/status")
    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_api_holdout_prediction_uses_only_local_model(monkeypatch, tmp_path):
    model = fitted_model()
    monkeypatch.setenv("F1_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APEX_PIT_MODEL_FILE", str(tmp_path / "pit.json"))
    model.save(tmp_path / "pit.json")
    sample_race(2024, 1).save(race_file(2024, 1))
    response = client.get("/api/v1/historical/2024/1/opponent-pit/17")
    assert response.status_code == 200
    data = response.json()
    assert data["holdout_race"] == "2024:1:R"
    assert data["as_of_leader_lap"] == 17


def test_api_in_sample_prediction_returns_422(monkeypatch, tmp_path):
    model = fitted_model()
    monkeypatch.setenv("F1_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APEX_PIT_MODEL_FILE", str(tmp_path / "pit.json"))
    model.save(tmp_path / "pit.json")
    sample_race(2023, 2).save(race_file(2023, 2))
    response = client.get("/api/v1/historical/2023/2/opponent-pit/17")
    assert response.status_code == 422

def test_later_season_must_not_train_earlier_holdout():
    model = train_pit_model([sample_race(2025, 1)])
    with pytest.raises(ValueError, match="Future-race training leakage"):
        model.predict_snapshot(sample_race(2024, 1).snapshot(10))
    with pytest.raises(ValueError, match="Future-race training leakage"):
        model.backtest(sample_race(2024, 1))
