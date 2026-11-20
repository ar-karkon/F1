"""Leakage-safe historical race replay with completed-lap temporal cutoffs.

A snapshot for leader lap N is constructed at the *earliest recorded lap-N
completion timestamp*, not by taking every driver's row with lap_number <= N.
That distinction matters: slower cars can finish lap N AFTER the leader and
those later records must not be exposed at the leader's decision point.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SOURCE = "FastF1 historical race timing"
OPENF1_SOURCE = "OpenF1 historical race timing"
ALLOWED_SOURCES = {SOURCE, OPENF1_SOURCE}


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class CompletedLap:
    driver: str
    lap_number: int
    end_session_seconds: float
    lap_seconds: float | None = None
    compound: str | None = None
    tyre_life: int | None = None
    stint: int | None = None
    position: int | None = None
    pit_in: bool = False
    pit_out: bool = False

    def validate(self) -> None:
        if not isinstance(self.driver, str) or not 2 <= len(self.driver) <= 5:
            raise ValueError("driver must be a driver abbreviation")
        _positive_int(self.lap_number, "lap_number")
        if _finite_number(self.end_session_seconds, "end_session_seconds") < 0:
            raise ValueError("end_session_seconds must not be negative")
        if self.lap_seconds is not None and _finite_number(self.lap_seconds, "lap_seconds") <= 0:
            raise ValueError("lap_seconds must be positive")
        if self.compound is not None and (
            not isinstance(self.compound, str) or len(self.compound) > 32
        ):
            raise ValueError("compound is invalid")
        for field in ("tyre_life", "stint", "position"):
            value = getattr(self, field)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ValueError(f"{field} is invalid")
        if not isinstance(self.pit_in, bool) or not isinstance(self.pit_out, bool):
            raise TypeError("pit flags must be boolean")


@dataclass
class HistoricalRace:
    year: int
    round_number: int
    laps: list[CompletedLap]
    session: str = "R"
    source: str = SOURCE

    def __post_init__(self) -> None:
        if not 2018 <= _positive_int(self.year, "year") <= 2100:
            raise ValueError("Unsupported season")
        if not 1 <= _positive_int(self.round_number, "round_number") <= 30:
            raise ValueError("Invalid round_number")
        if self.session != "R":
            raise ValueError("Replay currently supports full race sessions only")
        if self.source not in ALLOWED_SOURCES:
            raise ValueError("Unknown historical timing source")
        if not self.laps:
            raise ValueError("No completed laps available")
        seen: set[tuple[str, int]] = set()
        for row in self.laps:
            row.validate()
            ident = (row.driver, row.lap_number)
            if ident in seen:
                raise ValueError(f"Duplicate completed lap: {ident}")
            seen.add(ident)
        self.laps.sort(key=lambda row: (row.end_session_seconds, row.driver, row.lap_number))

    def boundaries(self) -> list[dict[str, int | float]]:
        """Earliest observed end timestamp for each completed lap number."""
        first: dict[int, float] = {}
        for lap in self.laps:
            first[lap.lap_number] = min(
                first.get(lap.lap_number, lap.end_session_seconds),
                lap.end_session_seconds,
            )
        return [
            {"lap": number, "session_seconds": round(first[number], 3)}
            for number in sorted(first)
        ]

    def snapshot(self, leader_lap: int) -> dict[str, Any]:
        """No full-race finishing result or future timing enters this snapshot."""
        lap = _positive_int(leader_lap, "lap")
        boundaries = {item["lap"]: item["session_seconds"] for item in self.boundaries()}
        if lap not in boundaries:
            raise ValueError(f"No leader completion timestamp for lap {lap}")
        cutoff = float(boundaries[lap])
        latest: dict[str, CompletedLap] = {}
        pit_counts: dict[str, int] = {}
        for row in self.laps:
            if row.end_session_seconds > cutoff:
                break
            latest[row.driver] = row
            if row.pit_in:
                pit_counts[row.driver] = pit_counts.get(row.driver, 0) + 1

        drivers = [
            {
                "driver": name,
                "last_completed_lap": row.lap_number,
                "last_seen_session_seconds": row.end_session_seconds,
                "last_lap_seconds": row.lap_seconds,
                "last_known_compound": row.compound,
                "last_known_tyre_life": row.tyre_life,
                "last_known_stint": row.stint,
                "last_reported_position": row.position,
                "observed_pit_ins": pit_counts.get(name, 0),
                "pit_in_on_last_lap": row.pit_in,
                "pit_out_on_last_lap": row.pit_out,
            }
            for name, row in latest.items()
        ]
        drivers.sort(key=lambda x: (x["last_reported_position"] is None,
                                    x["last_reported_position"] or 99, x["driver"]))
        return {
            "mode": "HISTORICAL_AS_OF_LEADER_LAP",
            "source": self.source,
            "season": self.year,
            "round": self.round_number,
            "session": self.session,
            "as_of_leader_lap": lap,
            "cutoff_session_seconds": cutoff,
            "drivers": drivers,
            "n_completed_records_visible": sum(
                row.end_session_seconds <= cutoff for row in self.laps
            ),
            "notes": [
                "Only completed laps with session Time <= this cutoff are visible.",
                "Positions are last-reported per driver, not simultaneous live positions.",
                "FastF1 historical timing may contain corrections published after the race.",
                "No model prediction, opponent inference or counterfactual result is included.",
            ],
        }

    def verify_chronology(self) -> dict[str, Any]:
        """Validate every available leader-lap snapshot, not just sample laps.

        Checks observed-record cardinality, monotonic temporal boundaries and
        that no driver card can represent a completion later than its cutoff.
        This does not prove live-field disclosure timestamps.
        """
        boundaries = self.boundaries()
        prev_cutoff = -1.0
        prev_count = 0
        for entry in boundaries:
            cutoff = float(entry["session_seconds"])
            if cutoff <= prev_cutoff:
                raise ValueError("Nonmonotonic leader lap timeline")
            current = self.snapshot(int(entry["lap"]))
            expected = sum(row.end_session_seconds <= cutoff for row in self.laps)
            if current["n_completed_records_visible"] != expected:
                raise ValueError("Snapshot contains an incorrect number of visible records")
            if expected < prev_count:
                raise ValueError("Visible record count decreased")
            if any(
                card["last_seen_session_seconds"] > cutoff
                for card in current["drivers"]
            ):
                raise ValueError("Future completed lap leaked into snapshot")
            prev_count = expected
            prev_cutoff = cutoff
        return {
            "chronological_snapshots_verified": len(boundaries),
            "records_in_final_snapshot": prev_count,
            "source": self.source,
            "note": "Historical time filtering verified; field-level disclosure unverified.",
        }

    def summary(self) -> dict[str, Any]:
        return {
            "mode": "HISTORICAL_IMPORTED",
            "source": self.source,
            "season": self.year,
            "round": self.round_number,
            "session": self.session,
            "completed_lap_records": len(self.laps),
            "driver_count": len({row.driver for row in self.laps}),
            "available_leader_laps": self.boundaries(),
            "has_predictions": False,
            "note": "Session retrospective; summary includes later laps. Never pass summary to a model at lap N.",
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "season": self.year,
            "round": self.round_number,
            "session": self.session,
            "source": self.source,
            "laps": [asdict(row) for row in self.laps],
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> HistoricalRace:
        if not isinstance(obj, dict) or obj.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported historical race schema")
        if obj.get("source") not in ALLOWED_SOURCES:
            raise ValueError("Unrecognized historical race data source")
        rows = obj.get("laps")
        if not isinstance(rows, list):
            raise TypeError("laps must be a list")
        return cls(
            year=obj["season"],
            round_number=obj["round"],
            session=obj["session"],
            source=obj["source"],
            laps=[CompletedLap(**record) for record in rows],
        )

    @classmethod
    def load(cls, path: Path) -> HistoricalRace:
        return cls.from_json(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
