"""Private JSON-stdin worker for an isolated TUM basic race-time calculation.

Never execute this module on data from an untrusted checkout. The root path is
explicitly selected by the parent Apex process. All model code remains upstream.
"""
from __future__ import annotations

import configparser
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


def main() -> None:
    request = json.load(sys.stdin)
    root = Path(request["root"])
    config_file = root / "racesim_basic/input/parameters/pars_YasMarina_2017.ini"
    module_file = root / "racesim_basic/src/calc_racetimes_basic.py"

    parser = configparser.ConfigParser()
    if not parser.read(config_file):
        raise FileNotFoundError(f"TUM sample configuration not found: {config_file}")
    race = json.loads(parser.get("RACE_PARS", "race_pars"))
    driver = json.loads(parser.get("DRIVER_PARS", "driver_pars"))
    track = json.loads(parser.get("TRACK_PARS", "track_pars"))
    total_laps = int(race["tot_no_laps"])

    # Load only the TUM basic time calculator: importing racesim_basic itself
    # would eagerly import cvxpy through its 2019 optimizer dependency graph.
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("_apex_pinned_tum_calc_racetimes_basic", module_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load TUM basic race time source")
    module = importlib.util.module_from_spec(spec)
    with redirect_stdout(io.StringIO()):
        spec.loader.exec_module(module)

    if driver["b_fuel_perlap"] is None:
        # Matches upstream import_pars.import_pars default calculation.
        driver["b_fuel_perlap"] = driver["m_fuel_init"] / total_laps

    rows = []
    with redirect_stdout(io.StringIO()):
        for inlap in request["pit_laps"]:
            strategy = [
                [0, request["start_compound"], 0, 0.0],
                [inlap, request["next_compound"], 0, 0.0],
            ]
            cumulative, _fcy_phases = module.calc_racetimes_basic(
                t_base=driver["t_base"],
                tot_no_laps=total_laps,
                t_lap_sens_mass=track["t_lap_sens_mass"],
                t_pitdrive_inlap=track["t_pitdrive_inlap"],
                t_pitdrive_outlap=track["t_pitdrive_outlap"],
                t_pit_tirechange=driver["t_pit_tirechange"],
                pits_aft_finishline=track["pits_aft_finishline"],
                tire_pars=driver["tire_pars"],
                p_grid=driver["p_grid"],
                t_loss_pergridpos=track["t_loss_pergridpos"],
                t_loss_firstlap=track["t_loss_firstlap"],
                strategy=strategy,
                drivetype=driver["drivetype"],
                m_fuel_init=driver["m_fuel_init"],
                b_fuel_perlap=driver["b_fuel_perlap"],
                t_pit_refuel_perkg=driver["t_pit_refuel_perkg"],
                t_pit_charge_perkwh=driver["t_pit_charge_perkwh"],
                t_pitdrive_inlap_fcy=track["t_pitdrive_inlap_fcy"],
                t_pitdrive_outlap_fcy=track["t_pitdrive_outlap_fcy"],
                t_pitdrive_inlap_sc=track["t_pitdrive_inlap_sc"],
                t_pitdrive_outlap_sc=track["t_pitdrive_outlap_sc"],
                fcy_phases=None,
                t_lap_sc=track["t_lap_sc"],
                t_lap_fcy=track["t_lap_fcy"],
            )
            if len(cumulative) != total_laps:
                raise RuntimeError("TUM returned an unexpected lap count")
            rows.append({
                "pit_inlap_index": inlap,
                "modelled_full_race_seconds": round(float(cumulative[-1]), 3),
                "lap_count": len(cumulative),
            })

    rows.sort(key=lambda row: (row["modelled_full_race_seconds"], row["pit_inlap_index"]))
    fastest = rows[0]["modelled_full_race_seconds"]
    for row in rows:
        row["delta_to_best_seconds"] = round(row["modelled_full_race_seconds"] - fastest, 3)

    report = {
        "mode": "UPSTREAM_TUM_2017_REFERENCE_EXAMPLE",
        "source_repo": "https://github.com/TUMFTM/race-simulation",
        "upstream_commit": "96ef2c2021982217be008fe458df47c1a72da071",
        "engine": "TUM racesim_basic.calc_racetimes_basic (original upstream module)",
        "parameter_source": "racesim_basic/input/parameters/pars_YasMarina_2017.ini",
        "race_laps": total_laps,
        "compounds": [request["start_compound"], request["next_compound"]],
        "recommended_pit_inlap_index": rows[0]["pit_inlap_index"],
        "strategies": rows,
        "runtime_executed": True,
        "notices": [
            "Uses old illustrative TUM 2017 reference parameters, not calibrated 2026 data.",
            "Full-race open-track model; not live, traffic-aware or 2026-regulation-aware.",
            "TUM upstream is LGPL-3.0; its source and copyright remain with its authors.",
            "Do not compare modelled times to real race outcomes or inferred victory odds.",
        ],
    }
    json.dump(report, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
