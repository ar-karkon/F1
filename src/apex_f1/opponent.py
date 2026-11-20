"""Leakage-conscious pit-window empirical baseline (research, NOT race operations).

Models probability a driver records a pit event within the NEXT H completed
driver laps after a completed observation, using old races only. Labels
require future records in training/backtest, but features never access them.
No ML/LLM needed; smoothed bin frequencies are auditable and reproducible.
"""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from apex_f1.replay import CompletedLap, HistoricalRace

MODEL_VERSION = "pit-window-baseline-v1"
DEFAULT_HORIZON = 3
MIN_TRAIN_EXAMPLES = 100


def model_file() -> Path:
    import os

    return Path(
        os.environ.get("APEX_PIT_MODEL_FILE", "data/derived/pit-window-model.json")
    ).expanduser()


def race_id(race: HistoricalRace) -> str:
    return f"{race.year}:{race.round_number}:R"


def _compound(compound: str | None) -> str:
    known = (compound or "").upper()
    return known if known in {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"} else "UNKNOWN"


def _age_bucket(age: int | None) -> str:
    if age is None or age < 0:
        return "unknown"
    if age < 10:
        return "0-9"
    if age < 20:
        return "10-19"
    if age < 30:
        return "20-29"
    return "30+"


def _stage(lap: int) -> str:
    if lap < 20:
        return "early"
    if lap < 40:
        return "middle"
    return "late"


def _keys(compound: str | None, tyre_age: int | None, lap: int) -> tuple[str, str]:
    basic = _compound(compound) + "|" + _age_bucket(tyre_age)
    return basic, basic + "|" + _stage(lap)


def _examples(
    race: HistoricalRace, horizon: int
) -> Iterator[tuple[CompletedLap, int]]:
    """Yield completed observations and outcomes for fully observable H-lap windows.

    Censoring rule: require each of the NEXT H driver laps to exist and be
    consecutive, so retirement, missing records, or race finish cannot be
    mistakenly counted as a negative outcome. The first pit within H is 1.
    """
    per_driver: dict[str, list[CompletedLap]] = defaultdict(list)
    for row in race.laps:
        per_driver[row.driver].append(row)
    for rows in per_driver.values():
        rows.sort(key=lambda row: row.lap_number)
        for index, observed in enumerate(rows):
            following = rows[index + 1:index + horizon + 1]
            if observed.pit_in or len(following) < horizon:
                continue
            if any(
                future.lap_number != observed.lap_number + offset
                for offset, future in enumerate(following, start=1)
            ):
                continue
            label = int(any(future.pit_in for future in following))
            yield observed, label


def _rate(counts: list[int], prior: float, strength: float) -> float:
    hits, total = counts
    return (hits + strength * prior) / (total + strength)


@dataclass
class PitModel:
    horizon: int
    training_races: list[str]
    example_count: int
    event_count: int
    by_compound_age: dict[str, list[int]]
    by_compound_age_stage: dict[str, list[int]]
    version: str = MODEL_VERSION

    def __post_init__(self) -> None:
        if self.version != MODEL_VERSION:
            raise ValueError("Unsupported pit model version")
        if not isinstance(self.horizon, int) or not 1 <= self.horizon <= 5:
            raise ValueError("Horizon must be 1–5 completed driver laps")
        if self.example_count < MIN_TRAIN_EXAMPLES or not 0 <= self.event_count <= self.example_count:
            raise ValueError("Insufficient training observations or invalid events")
        if len(set(self.training_races)) != len(self.training_races) or not self.training_races:
            raise ValueError("Invalid training race inventory")
        for table in (self.by_compound_age, self.by_compound_age_stage):
            for key, counts in table.items():
                if not isinstance(key, str) or not isinstance(counts, list) or len(counts) != 2:
                    raise ValueError("Invalid model bin")
                if any(not isinstance(x, int) or x < 0 for x in counts):
                    raise ValueError("Invalid model counts")
                if counts[0] > counts[1] or counts[1] > self.example_count:
                    raise ValueError("Inconsistent model bin")

    @property
    def global_prior(self) -> float:
        return (self.event_count + 2) / (self.example_count + 4)

    def probability(self, compound: str | None, age: int | None, lap: int) -> dict[str, Any]:
        basic, specific = _keys(compound, age, lap)
        basic_counts = self.by_compound_age.get(basic, [0, 0])
        fine_counts = self.by_compound_age_stage.get(specific, [0, 0])
        # Hierarchical smoothing keeps sparse combinations near the
        # empirical training prior instead of inventing extreme certainty.
        coarse = _rate(basic_counts, self.global_prior, 30.0)
        p = _rate(fine_counts, coarse, 40.0)
        if not isfinite(p) or not 0 < p < 1:
            raise ValueError("Model produced invalid probability")
        return {
            "pit_within_next_n_driver_laps_probability": round(p, 4),
            "horizon_driver_laps": self.horizon,
            "feature_bins": {
                "compound": _compound(compound),
                "tyre_age": _age_bucket(age),
                "race_stage": _stage(lap),
            },
            "support_count_specific_bin": fine_counts[1],
            "support_count_compound_age": basic_counts[1],
            "uncertainty": (
                "Low sample support: estimate mainly shrunk to historical base rate"
                if fine_counts[1] < 25
                else "Empirical frequency with shrinkage; not calibrated for live use"
            ),
        }

    def _assert_chronological_holdout(self, year: int, round_number: int) -> None:
        target = (year, round_number)
        for item in self.training_races:
            parts = item.split(":")
            if len(parts) != 3 or parts[2] != "R":
                raise ValueError("Malformed training race identifier")
            train_key = (int(parts[0]), int(parts[1]))
            if train_key == target:
                raise ValueError("In-sample race: choose an event excluded from training")
            if train_key > target:
                raise ValueError(
                    "Future-race training leakage: model must use chronologically earlier races"
                )

    def _assert_out_of_sample(self, race: HistoricalRace) -> None:
        self._assert_chronological_holdout(race.year, race.round_number)

    def predict_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        this_race = f"{snapshot['season']}:{snapshot['round']}:R"
        self._assert_chronological_holdout(snapshot["season"], snapshot["round"])
        cutoff = float(snapshot["cutoff_session_seconds"])
        rows = []
        for driver in snapshot["drivers"]:
            if float(driver["last_seen_session_seconds"]) > cutoff:
                raise ValueError("Future completed lap would leak into prediction")
            if driver["pit_in_on_last_lap"]:
                continue  # Decision immediately after pit entry is not comparable.
            pred = self.probability(
                driver["last_known_compound"],
                driver["last_known_tyre_life"],
                driver["last_completed_lap"],
            )
            rows.append({
                "driver": driver["driver"],
                "last_completed_lap": driver["last_completed_lap"],
                "last_known_compound": driver["last_known_compound"],
                "last_known_tyre_life": driver["last_known_tyre_life"],
                **pred,
            })
        rows.sort(key=lambda row: (
            -row["pit_within_next_n_driver_laps_probability"], row["driver"]
        ))
        return {
            "mode": "HISTORICAL_EMPIRICAL_PIT_WINDOW_BASELINE",
            "model_version": self.version,
            "training_races": self.training_races,
            "training_example_count": self.example_count,
            "training_event_rate": round(self.event_count / self.example_count, 4),
            "holdout_race": this_race,
            "as_of_leader_lap": snapshot["as_of_leader_lap"],
            "cutoff_session_seconds": cutoff,
            "prediction_target": (
                f"Observed pit event within next {self.horizon} *driver-completed* laps"
            ),
            "predictions": rows,
            "notices": [
                "Historical baseline only: not a validated team-specific strategy model.",
                "OpenF1 event timing approximations and retrospective field changes apply.",
                "Probabilities are smoothed bin frequencies, not an LLM opinion.",
                "Excludes rows immediately following a recorded pit-in; no pit decisions are issued.",
            ],
        }

    def backtest(self, race: HistoricalRace) -> dict[str, Any]:
        self._assert_out_of_sample(race)
        cases = list(_examples(race, self.horizon))
        if not cases:
            raise ValueError("Holdout race has no complete prediction windows")
        brier = 0.0
        naive_brier = 0.0
        actual = 0
        calibration: dict[str, list[float]] = {}
        for observed, label in cases:
            pred = self.probability(
                observed.compound, observed.tyre_life, observed.lap_number
            )["pit_within_next_n_driver_laps_probability"]
            brier += (pred - label) ** 2
            naive_brier += (self.global_prior - label) ** 2
            actual += label
            # Fixed probability bins, not chosen after looking at the holdout.
            bucket = min(4, int(pred * 5))
            key = f"{bucket / 5:.1f}-{(bucket + 1) / 5:.1f}"
            stats = calibration.setdefault(key, [0.0, 0.0, 0.0])
            stats[0] += 1
            stats[1] += pred
            stats[2] += label
        n = len(cases)
        calib_rows = [
            {
                "probability_bin": key,
                "count": int(v[0]),
                "mean_prediction": round(v[1] / v[0], 4),
                "observed_rate": round(v[2] / v[0], 4),
            }
            for key, v in sorted(calibration.items())
        ]
        return {
            "mode": "HISTORICAL_OUT_OF_SAMPLE_BACKTEST",
            "model_version": self.version,
            "holdout_race": race_id(race),
            "training_races": self.training_races,
            "horizon_driver_laps": self.horizon,
            "n_decision_windows": n,
            "n_positive_windows": actual,
            "holdout_event_rate": round(actual / n, 4),
            "training_base_rate": round(self.global_prior, 4),
            "brier_model": round(brier / n, 6),
            "brier_base_rate": round(naive_brier / n, 6),
            "brier_improvement_vs_base": round((naive_brier - brier) / n, 6),
            "better_than_base_on_this_race": brier < naive_brier,
            "calibration_bins": calib_rows,
            "notices": [
                "Single-race evaluation is not sufficient to establish generalization.",
                "Per-lap decision windows overlap and are not independent samples.",
                "Brier score: lower is better. Baseline is training-set global event rate.",
                "Model training and holdout use historical post-processed timing fields.",
                "No team-specific telemetry, track effects or simulated pit losses.",
            ],
        }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "horizon": self.horizon,
            "training_races": self.training_races,
            "example_count": self.example_count,
            "event_count": self.event_count,
            "by_compound_age": self.by_compound_age,
            "by_compound_age_stage": self.by_compound_age_stage,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> PitModel:
        return cls(**json.loads(path.read_text(encoding="utf-8")))


def train_pit_model(races: list[HistoricalRace], horizon: int = DEFAULT_HORIZON) -> PitModel:
    if not isinstance(horizon, int) or isinstance(horizon, bool) or not 1 <= horizon <= 5:
        raise ValueError("Horizon must be 1–5 driver laps")
    if not races:
        raise ValueError("No training races provided")
    ids = [race_id(race) for race in races]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate training race")
    basic_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    specific_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    total, positives = 0, 0
    for race in races:
        for row, label in _examples(race, horizon):
            basic, specific = _keys(row.compound, row.tyre_life, row.lap_number)
            basic_counts[basic][0] += label
            basic_counts[basic][1] += 1
            specific_counts[specific][0] += label
            specific_counts[specific][1] += 1
            total += 1
            positives += label
    return PitModel(
        horizon=horizon,
        training_races=sorted(ids),
        example_count=total,
        event_count=positives,
        by_compound_age=dict(basic_counts),
        by_compound_age_stage=dict(specific_counts),
    )
