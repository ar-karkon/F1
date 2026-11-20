"""Explicit FastF1 historical race importer. Requires optional `.[data]` extra."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from apex_f1.replay import CompletedLap, HistoricalRace


def race_data_dir() -> Path:
    return Path(os.environ.get("F1_DATA_DIR", "data/derived")).expanduser()


def race_file(year: int, round_number: int) -> Path:
    if not 2018 <= year <= 2100 or not 1 <= round_number <= 30:
        raise ValueError("Invalid historical race identifier")
    return race_data_dir() / f"race-{year}-round-{round_number}-R.json"


def import_fastf1_race(year: int, round_number: int) -> HistoricalRace:
    """Import completed-lap timing only; no car telemetry or timing beyond lap end.

    FastF1's lap data is a historical post-processed source, not a real-time
    timing feed. F1 may correct timestamps or track status after a race.
    """
    try:
        import fastf1
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError('Install the FastF1 dependency: pip install -e ".[data]"') from exc

    if not 2018 <= year <= datetime.now(timezone.utc).year:
        raise ValueError("Race season is outside the historical data window")
    if not 1 <= round_number <= 30:
        raise ValueError("Race round must be between 1 and 30")

    cache = Path(os.environ.get("F1_FASTF1_CACHE_DIR", "data/cache/fastf1"))
    cache.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache))
    session = fastf1.get_session(year, round_number, "R")
    session.load(laps=True, telemetry=False, weather=False, messages=False)
    if session.laps is None or session.laps.empty:
        raise ValueError("FastF1 returned no race laps")

    def scalar(value):
        if value is None or pd.isna(value):
            return None
        return value

    def seconds(value):
        obj = scalar(value)
        if obj is None:
            return None
        return float(obj.total_seconds())

    def integer(value):
        obj = scalar(value)
        return None if obj is None else int(obj)

    completed = []
    seen = set()
    for _, lap in session.laps.iterrows():
        driver = scalar(lap.get("Driver"))
        number = integer(lap.get("LapNumber"))
        end_time = seconds(lap.get("Time"))
        if not isinstance(driver, str) or number is None or number < 1:
            continue
        if end_time is None or end_time < 0:
            continue  # Exclude missing completion timestamps; never impute using future rows.
        if (driver, number) in seen:
            raise ValueError(f"Duplicate FastF1 lap for {driver}, lap {number}")
        seen.add((driver, number))
        lap_time = seconds(lap.get("LapTime"))
        compound = scalar(lap.get("Compound"))
        completed.append(
            CompletedLap(
                driver=driver,
                lap_number=number,
                end_session_seconds=round(end_time, 3),
                lap_seconds=round(lap_time, 3) if lap_time and lap_time > 0 else None,
                compound=str(compound) if compound is not None else None,
                tyre_life=integer(lap.get("TyreLife")),
                stint=integer(lap.get("Stint")),
                position=integer(lap.get("Position")),
                pit_in=scalar(lap.get("PitInTime")) is not None,
                pit_out=scalar(lap.get("PitOutTime")) is not None,
            )
        )
    return HistoricalRace(year=year, round_number=round_number, laps=completed)


def import_to_file(
    year: int, round_number: int, output: str | None = None, provider: str = "openf1"
) -> Path:
    if provider == "openf1":
        from apex_f1.openf1_import import import_openf1_race

        history = import_openf1_race(year, round_number)
    elif provider == "fastf1":
        history = import_fastf1_race(year, round_number)
    else:
        raise ValueError("provider must be 'openf1' or 'fastf1'")
    target = Path(output) if output else race_file(year, round_number)
    return history.save(target)
