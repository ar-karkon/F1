"""Chronological calibration and multi-race out-of-sample pit-out benchmark.

A single intercept correction is fitted using ONLY distinct calibration races,
then frozen for later test races. This is a deliberately small calibration model;
it cannot create information about weather, safety cars or rival intentions.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from apex_f1.opponent import MODEL_VERSION, PitModel, _examples, race_id
from apex_f1.replay import HistoricalRace

CALIBRATOR_VERSION = "pit-out-logit-intercept-v1"
RIDGE_PSEUDOCOUNT = 20.0


def calibration_file() -> Path:
    return Path(
        os.environ.get("APEX_PIT_CALIBRATOR_FILE", "data/derived/pit-window-calibrator.json")
    ).expanduser()


def _signature(model: PitModel) -> str:
    """Prevent accidentally applying a calibration to a re-trained model."""
    return hashlib.sha256(
        json.dumps(asdict(model), sort_keys=True).encode("utf-8")
    ).hexdigest()


def _chronology(key: str) -> tuple[int, int]:
    tokens = key.split(":")
    if len(tokens) != 3 or tokens[2] != "R":
        raise ValueError("Invalid race key, expected YEAR:ROUND:R")
    return int(tokens[0]), int(tokens[1])


def _logit(value: float) -> float:
    p = min(1.0 - 1e-6, max(1e-6, value))
    return math.log(p / (1 - p))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


@dataclass(frozen=True)
class InterceptCalibrator:
    model_version: str
    model_fingerprint: str
    model_training_races: list[str]
    calibration_races: list[str]
    intercept: float
    calibration_windows: int
    calibration_positive: int
    version: str = CALIBRATOR_VERSION

    def __post_init__(self) -> None:
        if self.version != CALIBRATOR_VERSION or self.model_version != MODEL_VERSION:
            raise ValueError("Unsupported calibration/model version")
        if len(self.model_fingerprint) != 64:
            raise ValueError("Missing or invalid model fingerprint")
        if not math.isfinite(self.intercept) or abs(self.intercept) > 3.00001:
            raise ValueError("Calibration intercept out of fixed bounds")
        if self.calibration_windows < 100:
            raise ValueError("Insufficient calibration windows")
        if not 0 < self.calibration_positive < self.calibration_windows:
            raise ValueError("Calibration requires both positive and negative outcomes")
        if len(set(self.calibration_races)) != len(self.calibration_races):
            raise ValueError("Duplicate calibration races")
        if len(self.calibration_races) < 2 or not self.model_training_races:
            raise ValueError("Calibration needs two races and a trained base model")
        if max(map(_chronology, self.model_training_races)) >= min(
            map(_chronology, self.calibration_races)
        ):
            raise ValueError("Calibration must occur after all model-training races")

    def apply(self, value: float) -> float:
        """A time-independent calibrated probability, never a new prediction."""
        return _sigmoid(_logit(value) + self.intercept)

    def ensure_compatible(self, model: PitModel) -> None:
        if (
            self.model_version != model.version
            or self.model_training_races != model.training_races
            or self.model_fingerprint != _signature(model)
        ):
            raise ValueError("Calibrator fitted for a different base model")

    def ensure_test(self, model: PitModel, race: HistoricalRace) -> None:
        self.ensure_compatible(model)
        model._assert_out_of_sample(race)
        if _chronology(race_id(race)) <= max(
            map(_chronology, self.calibration_races)
        ):
            raise ValueError("Test race must occur AFTER calibration; leakage prevented")

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> InterceptCalibrator:
        return cls(**json.loads(path.read_text(encoding="utf-8")))


def _proba(model: PitModel, row: Any) -> float:
    return model.probability(
        row.compound, row.tyre_life, row.lap_number
    )["pit_within_next_n_driver_laps_probability"]


def fit_calibrator(
    model: PitModel,
    calibration_races: list[HistoricalRace],
) -> InterceptCalibrator:
    if len(calibration_races) < 2:
        raise ValueError("At least two distinct calibration races are required")
    ids = [race_id(r) for r in calibration_races]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate calibration race")
    for race in calibration_races:
        model._assert_out_of_sample(race)
    if max(map(_chronology, model.training_races)) >= min(
        map(_chronology, ids)
    ):
        raise ValueError("Calibration races must be later than training races")

    points: list[tuple[float, int]] = []
    for race in calibration_races:
        points.extend((_logit(_proba(model, row)), y) for row, y in
                      _examples(race, model.horizon))
    n = len(points)
    actual = sum(y for _, y in points)
    if n < 100 or not 0 < actual < n:
        raise ValueError("Calibration sample insufficient or lacks class diversity")

    # Fixed-prior regularized intercept: solve monotonic log-loss gradient.
    # Regularization discourages a two-race-only fit from overcorrecting.
    low, high = -3.0, 3.0
    for _ in range(55):
        mid = (low + high) / 2
        gradient = sum(_sigmoid(z + mid) - y for z, y in points)
        gradient += RIDGE_PSEUDOCOUNT * mid
        if gradient > 0:
            high = mid
        else:
            low = mid

    return InterceptCalibrator(
        model_version=model.version,
        model_fingerprint=_signature(model),
        model_training_races=model.training_races.copy(),
        calibration_races=ids,
        intercept=round((low + high) / 2, 8),
        calibration_windows=n,
        calibration_positive=actual,
    )


def _metrics(rows: list[tuple[float, float, float, int]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Cannot calculate metrics with no held-out windows")
    n = len(rows)
    names = ("base", "raw", "calibrated")
    error = {
        name: sum((point[i] - point[3]) ** 2 for point in rows) / n
        for i, name in enumerate(names)
    }
    log_loss = {
        name: -sum(
            y * math.log(min(1 - 1e-9, max(1e-9, point[i])))
            + (1 - y) * math.log(min(1 - 1e-9, max(1e-9, 1 - point[i])))
            for point in rows for y in [point[3]]
        ) / n
        for i, name in enumerate(names)
    }
    ece: dict[str, float] = {}
    calibration: dict[str, list[dict[str, Any]]] = {}
    for i, name in enumerate(names):
        bins: dict[int, list[float]] = {}
        for point in rows:
            k = min(9, int(point[i] * 10))
            stats = bins.setdefault(k, [0.0, 0.0, 0.0])
            stats[0] += 1
            stats[1] += point[i]
            stats[2] += point[3]
        ece[name] = sum(
            abs(stats[1] / stats[0] - stats[2] / stats[0]) * stats[0] / n
            for stats in bins.values()
        )
        calibration[name] = [
            {
                "band": f"{idx / 10:.1f}-{(idx + 1) / 10:.1f}",
                "count": int(stats[0]),
                "mean_predicted": round(stats[1] / stats[0], 4),
                "observed_rate": round(stats[2] / stats[0], 4),
            }
            for idx, stats in sorted(bins.items())
        ]
    return {
        "decision_windows": n,
        "positive_windows": sum(point[3] for point in rows),
        "observed_event_rate": round(sum(point[3] for point in rows) / n, 5),
        "brier": {k: round(v, 6) for k, v in error.items()},
        "log_loss": {k: round(v, 6) for k, v in log_loss.items()},
        "expected_calibration_error_10_bins": {
            k: round(v, 6) for k, v in ece.items()
        },
        "reliability_bins": calibration,
        "calibrated_improves_over_raw": error["calibrated"] < error["raw"],
        "calibrated_beats_base_rate": error["calibrated"] < error["base"],
    }


def evaluate_races(
    model: PitModel,
    calibrator: InterceptCalibrator,
    test_races: list[HistoricalRace],
) -> dict[str, Any]:
    if len(test_races) < 2:
        raise ValueError("Use at least two separate held-out test races")
    ids = [race_id(r) for r in test_races]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate test race")
    report = []
    pooled: list[tuple[float, float, float, int]] = []
    for race in test_races:
        calibrator.ensure_test(model, race)
        cases = list(_examples(race, model.horizon))
        rows = [
            (model.global_prior, p, calibrator.apply(p), label)
            for observed, label in cases
            for p in [_proba(model, observed)]
        ]
        if not rows:
            raise ValueError(f"No complete windows for {race_id(race)}")
        pooled.extend(rows)
        report.append({
            "race": race_id(race),
            "metrics": _metrics(rows),
        })
    aggregate = _metrics(pooled)
    return {
        "mode": "CHRONOLOGICAL_MULTIRACE_OUT_OF_SAMPLE_BACKTEST",
        "target": "OpenF1 pit-out lap in next N completed driver laps, excluding race lap 1",
        "model_version": model.version,
        "calibrator_version": calibrator.version,
        "train_races": model.training_races,
        "calibration_races": calibrator.calibration_races,
        "test_races": ids,
        "base_model_train_windows": model.example_count,
        "calibration_windows": calibrator.calibration_windows,
        "calibration_positive_windows": calibrator.calibration_positive,
        "calibration_intercept": calibrator.intercept,
        "horizon_driver_laps": model.horizon,
        "per_race": report,
        "pooled": aggregate,
        "methodology": [
            "All three data partitions are strictly ordered by (season, race round).",
            "Intercept chosen using calibration races only; never fitted on test races.",
            "Brier and log loss: lower is better. Baseline is frozen training-only base rate.",
            "10-bin ECE is descriptive, not a proof of reliability.",
            "Overlapping windows and shared drivers create dependence, so no independent-sample CI.",
            "OpenF1 retrospective tyre fields and approximate times may not equal live availability.",
            "Pit-out flags can include non-strategic pit lane activity.",
            "No LLM generated these numeric predictions or benchmark scores.",
            "OpenF1 historical research access is not a commercial data license.",
        ],
    }
