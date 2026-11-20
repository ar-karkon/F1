import pytest

from apex_f1.simulator import RaceState, evaluate_strategies


def test_deterministic_replay():
    a = evaluate_strategies(RaceState(), trials=75, seed=7)
    b = evaluate_strategies(RaceState(), trials=75, seed=7)
    assert a == b
    assert a["mode"] == "SYNTHETIC_UNVALIDATED"


def test_candidate_probabilities_sum_to_one():
    result = evaluate_strategies(RaceState(), trials=200, seed=42)
    rows = result["strategies"]
    assert len(rows) == 3
    assert sum(row["probability_fastest_of_candidates"] for row in rows) == pytest.approx(1, abs=0.0002)
    assert rows[0]["delta_to_best_seconds"] == pytest.approx(0)
    assert rows == sorted(rows, key=lambda row: row["expected_remaining_seconds"])


def test_stay_out_has_no_pit():
    rows = evaluate_strategies(RaceState(), 30)["strategies"]
    assert next(r for r in rows if r["key"] == "stay_out")["pit_lap"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"current_lap": 57},
        {"total_laps": 101},
        {"safety_car_probability": -0.1},
        {"current_compound": "ULTRASOFT"},
        {"pit_loss_seconds": 0},
    ],
)
def test_invalid_state(changes):
    state = RaceState(**{**RaceState().__dict__, **changes})
    with pytest.raises(ValueError):
        evaluate_strategies(state, 30)


def test_invalid_trials():
    with pytest.raises(ValueError):
        evaluate_strategies(RaceState(), trials=1)
