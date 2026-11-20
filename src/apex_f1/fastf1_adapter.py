"""Optional historical FastF1 export; never represents live team telemetry."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def export_driver_laps(
    year: int, round_number: int, session_code: str, driver: str, output: str
) -> Path:
    try:
        import fastf1
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError('Install data extras: pip install -e ".[data]"') from exc

    if not 2018 <= year <= datetime.now(timezone.utc).year:
        raise ValueError("Year outside supported historical range")
    if not 1 <= round_number <= 30:
        raise ValueError("Invalid race round")
    session = fastf1.get_session(year, round_number, session_code)
    session.load(laps=True, telemetry=False, weather=False, messages=False)
    laps = session.laps.pick_drivers(driver.upper())
    rows = []
    for _, lap in laps.iterrows():
        lap_time = lap.get("LapTime")
        lap_number = lap.get("LapNumber")
        if pd.isna(lap_number):
            continue
        rows.append({
            "lap_number": int(lap_number),
            "lap_seconds": None if pd.isna(lap_time) else round(lap_time.total_seconds(), 3),
            "compound": None if pd.isna(lap.get("Compound")) else str(lap["Compound"]),
            "tyre_life": None if pd.isna(lap.get("TyreLife")) else int(lap["TyreLife"]),
            "stint": None if pd.isna(lap.get("Stint")) else int(lap["Stint"]),
        })
    if not rows:
        raise ValueError("No laps found for the selected driver and session")
    result = {
        "source": "FastF1 historical data",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "year": year,
        "round": round_number,
        "session": session_code,
        "driver": driver.upper(),
        "laps": rows,
        "note": "Historical export only; NOT fitted to toy race simulator.",
    }
    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return dest
