"""Execute a pinned TUM full-race basic lap-time kernel in an isolated subprocess.

Upstream: https://github.com/TUMFTM/race-simulation (LGPL-3.0).
Uses the original upstream module and its 2017 Yas Marina sample configuration.
No upstream source is copied into Apex; no paid API, training or race data used.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from apex_f1.integrations.paths import upstream_path

TUM_COMMIT = "96ef2c2021982217be008fe458df47c1a72da071"
TUM_CONFIG = "pars_YasMarina_2017.ini"


class UpstreamUnavailable(RuntimeError):
    """Research dependency not checked out or installed."""


class UpstreamExecutionError(RuntimeError):
    """Isolated upstream subprocess did not complete successfully."""


def probe_tum(root: Path | None = None) -> dict[str, Any]:
    path = root or upstream_path("race-simulation")
    entry = path / "racesim_basic/src/calc_racetimes_basic.py"
    config = path / "racesim_basic/input/parameters" / TUM_CONFIG
    return {
        "name": "TUM Race Simulation",
        "pinned_commit": TUM_COMMIT,
        "source_present": entry.is_file() and config.is_file(),
        "entrypoint": "racesim_basic.src.calc_racetimes_basic.calc_racetimes_basic",
        "calibration": "TUM illustrative 2017 Yas Marina sample parameters",
        "runtime_executed": False,
        "status": "SOURCE_READY" if entry.is_file() and config.is_file() else "NOT_CHECKED_OUT",
    }


def compare_tum_example(
    pit_laps: list[int] | None = None,
    start_compound: str = "A4",
    next_compound: str = "A3",
    root: Path | None = None,
) -> dict[str, Any]:
    """Compare one-stop schedules with original TUM basic race-time equations.

    `pit_laps` are upstream inlap indices, not our existing synthetic demo's
    live-decision lap indices. No attempt is made to combine the two outputs.
    """
    directory = root or upstream_path("race-simulation")
    if not probe_tum(directory)["source_present"]:
        raise UpstreamUnavailable(
            "Pinned TUM source missing. Run: git submodule update --init "
            "third_party/race-simulation"
        )
    if pit_laps is None:
        pit_laps = [18, 25, 32]
    if not 1 <= len(pit_laps) <= 10 or len(pit_laps) != len(set(pit_laps)):
        raise ValueError("Provide 1 to 10 distinct pit_laps")
    if any(isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 54 for v in pit_laps):
        raise ValueError("Pit lap indices must be integers in [1, 54] for 55-lap Yas Marina")
    if start_compound not in {"A3", "A4", "A5"} or next_compound not in {"A3", "A4", "A5"}:
        raise ValueError("Supported example compounds: A3, A4, A5")
    if start_compound == next_compound:
        raise ValueError("Use distinct compounds in the supplied one-stop examples")

    request = {
        "root": str(directory.resolve()),
        "pit_laps": sorted(pit_laps),
        "start_compound": start_compound,
        "next_compound": next_compound,
    }
    try:
        process = subprocess.run(
            [sys.executable, "-m", "apex_f1.integrations.tum_worker"],
            input=json.dumps(request), text=True, capture_output=True,
            timeout=30, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise UpstreamExecutionError("TUM adapter timed out after 30 seconds") from exc
    if process.returncode != 0:
        # Upstream exceptions may disclose local paths but no input secrets are used.
        details = process.stderr.strip().splitlines()
        tail = details[-1] if details else "No stderr returned"
        raise UpstreamExecutionError(f"TUM worker failed: {tail[:350]}")
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise UpstreamExecutionError("TUM worker returned non-JSON output") from exc
    if not isinstance(result, dict) or "strategies" not in result:
        raise UpstreamExecutionError("TUM worker result missing strategies")
    return result
