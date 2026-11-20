"""Credential-free OpenF1 historical race importer for research/personal use.

OpenF1 historical REST API: https://openf1.org/docs/
Usage rights: https://openf1.org/ (research/non-commercial; commercial use
requires explicit rights discussion). Never copy raw API responses to Git.
"""
from __future__ import annotations

import json
import time
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from apex_f1.replay import OPENF1_SOURCE, CompletedLap, HistoricalRace

API_BASE = "https://api.openf1.org/v1"
USER_AGENT = "ApexF1-Research/0.1 (historical replay)"


def _utc_seconds(value: str) -> float:
    if not isinstance(value, str):
        raise TypeError("Missing event timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("OpenF1 timestamp must include timezone")
    return parsed.timestamp()


def _get_json(endpoint: str, **query: object) -> list[dict]:
    """Only allow predefined API paths and bounded HTTPS requests."""
    if endpoint not in {"sessions", "drivers", "laps", "stints", "pit", "position"}:
        raise ValueError("Unsupported OpenF1 endpoint")
    params = urlencode(query)
    request = Request(
        f"{API_BASE}/{endpoint}?{params}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(15_000_001)
    except OSError as exc:
        raise RuntimeError(f"OpenF1 {endpoint} request failed: {exc}") from exc
    if len(payload) > 15_000_000:
        raise RuntimeError(f"OpenF1 {endpoint} response exceeded size limit")
    result = json.loads(payload)
    if not isinstance(result, list):
        raise TypeError(f"Unexpected OpenF1 response from {endpoint}")
    return result


def _integer(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (ValueError, TypeError, OverflowError):
        return None


def _duration(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    n = float(value)
    return n if 0 < n < 1800 else None


def _sorted_events(rows: list[dict]) -> dict[int, tuple[list[float], list[int]]]:
    indexed: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for row in rows:
        driver = _integer(row.get("driver_number"))
        position = _integer(row.get("position"))
        try:
            stamp = _utc_seconds(row.get("date"))
        except (TypeError, ValueError):
            continue
        if driver is not None and position is not None and position > 0:
            indexed[driver].append((stamp, position))
    result = {}
    for driver, pairs in indexed.items():
        pairs.sort()
        result[driver] = ([x[0] for x in pairs], [x[1] for x in pairs])
    return result


def _asof_position(
    driver: int, at: float, events: dict[int, tuple[list[float], list[int]]]
) -> int | None:
    if driver not in events:
        return None
    times, values = events[driver]
    idx = bisect_right(times, at) - 1
    return values[idx] if idx >= 0 else None


def build_openf1_history(
    *,
    year: int,
    round_number: int,
    session_start: str,
    laps: list[dict],
    drivers: list[dict],
    stints: list[dict],
    pits: list[dict],
    positions: list[dict],
) -> HistoricalRace:
    """Pure conversion; testable offline with event fixtures (no network).

    Completion at start+duration is approximate in OpenF1; missing duration
    may be filled ONLY by the immediately following lap's start (same driver).
    No future tyre/position/pit information is exposed in an earlier lap row.
    """
    origin = _utc_seconds(session_start)
    acronyms = {
        _integer(row.get("driver_number")): row.get("name_acronym")
        for row in drivers
    }
    by_driver: dict[int, list[dict]] = defaultdict(list)
    for row in laps:
        driver, number = _integer(row.get("driver_number")), _integer(row.get("lap_number"))
        if driver is not None and number is not None and number > 0:
            by_driver[driver].append(row)

    stints_by_driver: dict[int, list[dict]] = defaultdict(list)
    for row in stints:
        driver, first_lap = _integer(row.get("driver_number")), _integer(row.get("lap_start"))
        if driver is not None and first_lap is not None and first_lap > 0:
            stints_by_driver[driver].append(row)
    for rows in stints_by_driver.values():
        rows.sort(key=lambda x: int(x["lap_start"]))

    # The pit endpoint's lap_number does not necessarily indicate the
    # completed lap whose timestamp covers the pit-lane passage. Associate
    # pit events by their own UTC timestamp, and reveal each ONLY at the
    # first subsequent completed lap for that driver. Otherwise later stops
    # can disappear or be incorrectly backdated.
    pit_by_driver: dict[int, list[float]] = defaultdict(list)
    for row in pits:
        driver = _integer(row.get("driver_number"))
        try:
            stamp = _utc_seconds(row.get("date"))
        except (TypeError, ValueError):
            continue
        if driver is not None:
            pit_by_driver[driver].append(stamp)
    for timestamps in pit_by_driver.values():
        timestamps.sort()
    position_events = _sorted_events(positions)
    completed = []
    used: set[tuple[int, int]] = set()

    for driver, rows in by_driver.items():
        rows.sort(key=lambda x: int(x["lap_number"]))
        pit_times = pit_by_driver[driver]
        next_pit_index = 0
        for i, row in enumerate(rows):
            number = int(row["lap_number"])
            if (driver, number) in used:
                raise ValueError(f"OpenF1 duplicate lap for driver {driver}, lap {number}")
            used.add((driver, number))
            try:
                start = _utc_seconds(row["date_start"])
            except (ValueError, TypeError, KeyError):
                continue
            duration = _duration(row.get("lap_duration"))
            if duration is not None:
                end = start + duration
            elif i + 1 < len(rows) and _integer(rows[i + 1].get("lap_number")) == number + 1:
                try:
                    end = _utc_seconds(rows[i + 1]["date_start"])
                except (ValueError, TypeError, KeyError):
                    continue
            else:
                continue
            if end <= origin:
                continue
            chosen = None
            for stint in stints_by_driver[driver]:
                if int(stint["lap_start"]) <= number:
                    chosen = stint
                else:
                    break
            compound = chosen.get("compound") if chosen else None
            stint_number = _integer(chosen.get("stint_number")) if chosen else None
            age_at_start = _integer(chosen.get("tyre_age_at_start")) if chosen else None
            tyre_age = (
                age_at_start + number - int(chosen["lap_start"]) + 1
                if age_at_start is not None else None
            )
            pit_visible = False
            while next_pit_index < len(pit_times) and pit_times[next_pit_index] <= end:
                pit_visible = True
                next_pit_index += 1
            driver_name = acronyms.get(driver)
            if not isinstance(driver_name, str) or not 2 <= len(driver_name) <= 5:
                driver_name = f"#{driver}"
            completed.append(
                CompletedLap(
                    driver=driver_name,
                    lap_number=number,
                    end_session_seconds=round(end - origin, 3),
                    lap_seconds=round(duration, 3) if duration is not None else None,
                    compound=compound if isinstance(compound, str) else None,
                    tyre_life=tyre_age,
                    stint=stint_number,
                    position=_asof_position(driver, end, position_events),
                    pit_in=pit_visible,
                    pit_out=bool(row.get("is_pit_out_lap") is True),
                )
            )
    if not completed:
        raise ValueError("OpenF1 returned no usable completed laps")
    return HistoricalRace(
        year=year, round_number=round_number,
        laps=completed, source=OPENF1_SOURCE,
    )


def import_openf1_race(year: int, round_number: int) -> HistoricalRace:
    """Select a historical main GP race by chronological year/round order."""
    if not 2023 <= year <= datetime.now(timezone.utc).year:
        raise ValueError("OpenF1 historical data starts in 2023")
    if not 1 <= round_number <= 30:
        raise ValueError("Invalid race round")
    sessions = _get_json("sessions", year=year, session_name="Race")
    races = [
        item for item in sessions
        if item.get("session_name") == "Race"
        and item.get("year") == year
        and not item.get("is_cancelled", False)
        and isinstance(item.get("date_start"), str)
        and isinstance(item.get("session_key"), int)
    ]
    races.sort(key=lambda item: item["date_start"])
    if round_number > len(races):
        raise ValueError(f"Only {len(races)} historical races listed for {year}")
    selected = races[round_number - 1]
    if _utc_seconds(selected["date_start"]) >= datetime.now(timezone.utc).timestamp():
        raise ValueError("Selected race has not started")
    session_key = selected["session_key"]
    # Keep under the public historical API's 3 req/s; stop and report errors.
    raw = {}
    for endpoint in ("drivers", "laps", "stints", "pit", "position"):
        time.sleep(0.38)
        raw[endpoint] = _get_json(endpoint, session_key=session_key)
    return build_openf1_history(
        year=year, round_number=round_number,
        session_start=selected["date_start"],
        laps=raw["laps"], drivers=raw["drivers"], stints=raw["stints"],
        pits=raw["pit"], positions=raw["position"],
    )
