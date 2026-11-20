"""Aggregate diagnostic: relate OpenF1 pit timestamps to lap completion cutoffs.

This explicitly downloads PUBLIC HISTORICAL research data. It prints only
small aggregate counts and a few timestamp offsets, never raw telemetry.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from apex_f1.historical_import import race_file
from apex_f1.openf1_import import _get_json, _integer, _utc_seconds
from apex_f1.replay import HistoricalRace


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=2024)
    p.add_argument("--round", type=int, default=4)
    args = p.parse_args()

    sessions = _get_json("sessions", year=args.year, session_name="Race")
    sessions = sorted(
        [x for x in sessions if x.get("session_name") == "Race"
         and x.get("year") == args.year], key=lambda x: x["date_start"]
    )
    session = sessions[args.round - 1]
    original = _utc_seconds(session["date_start"])
    key = session["session_key"]
    pits = _get_json("pit", session_key=key)
    drivers = _get_json("drivers", session_key=key)
    acronyms = {_integer(x.get("driver_number")): x.get("name_acronym") for x in drivers}
    history = HistoricalRace.load(race_file(args.year, args.round))
    grouped = defaultdict(dict)
    for row in history.laps:
        grouped[row.driver][row.lap_number] = row
    offsets = []
    seen = 0
    for pit in pits:
        driver = acronyms.get(_integer(pit.get("driver_number")))
        number = _integer(pit.get("lap_number"))
        if driver is None or number is None:
            continue
        match = grouped[driver].get(number)
        if match is None:
            continue
        try:
            event = _utc_seconds(pit["date"]) - original
        except (ValueError, TypeError, KeyError):
            continue
        seen += 1
        before = grouped[driver].get(number - 1)
        after = grouped[driver].get(number + 1)
        offsets.append({
            "event_lap": number,
            "event_minus_same_lap_completion_s": round(event - match.end_session_seconds, 2),
            "event_minus_previous_lap_completion_s": (
                round(event - before.end_session_seconds, 2) if before else None
            ),
            "event_minus_next_lap_completion_s": (
                round(event - after.end_session_seconds, 2) if after else None
            ),
        })
    print(json.dumps({
        "mode": "OPENF1_PIT_TIMESTAMP_AUDIT",
        "race": f"{args.year}:{args.round}:R",
        "raw_pit_event_count": len(pits),
        "events_matching_driver_and_lap": seen,
        "imported_pit_in_flags": sum(row.pit_in for row in history.laps),
        "imported_pit_out_flags": sum(row.pit_out for row in history.laps),
        "sample_timestamp_offsets": offsets[:8],
    }, indent=2))


if __name__ == "__main__":
    main()
