"""CLI entry points for offline evaluation, API, and optional historic data export."""
from __future__ import annotations

import argparse
import json

from apex_f1.simulator import RaceState, evaluate_strategies


def main() -> None:
    parser = argparse.ArgumentParser(prog="apex-f1", description="Apex F1 research utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run a seeded synthetic strategy scenario")
    demo.add_argument("--trials", type=int, default=400)
    demo.add_argument("--seed", type=int, default=7)

    serve = subparsers.add_parser("serve", help="Start the local API and dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    export = subparsers.add_parser("export-fastf1", help="Export historical driver laps")
    export.add_argument("--year", type=int, required=True)
    export.add_argument("--round", type=int, required=True)
    export.add_argument("--session", default="R")
    export.add_argument("--driver", required=True)
    export.add_argument("--output", required=True)

    tum = subparsers.add_parser("tum-compare", help="Run actual TUM 2017 basic reference model")
    tum.add_argument("--pit-laps", type=int, nargs="+", default=[18, 25, 32])
    tum.add_argument("--start-compound", choices=["A3", "A4", "A5"], default="A4")
    tum.add_argument("--next-compound", choices=["A3", "A4", "A5"], default="A3")

    subparsers.add_parser("integrations", help="Inspect pinned upstream source readiness")
    subparsers.add_parser(
        "llm-smoke", help="Explicitly test configured LLM API without sending any race data"
    )

    for name, help_text in (
        ("import-race", "Fetch historical FastF1 laps into ignored local storage"),
        ("replay-summary", "Inspect a locally imported historical race"),
        ("replay-lap", "Render as-of leader lap state without future laps"),
        ("replay-report", "Produce a compact verification report without raw lap data"),
    ):
        historical = subparsers.add_parser(name, help=help_text)
        historical.add_argument("--year", type=int, default=2024)
        historical.add_argument("--round", type=int, default=1)
        if name == "import-race":
            historical.add_argument("--output", default=None)
            historical.add_argument(
                "--provider", choices=["openf1", "fastf1"], default="openf1",
                help="OpenF1 historical API works without credentials; FastF1 may need F1 login",
            )
        if name == "replay-lap":
            historical.add_argument("--lap", type=int, required=True)

    args = parser.parse_args()
    if args.command == "demo":
        print(json.dumps(evaluate_strategies(RaceState(), args.trials, args.seed), indent=2))
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("apex_f1.api:app", host=args.host, port=args.port)
    elif args.command == "tum-compare":
        from apex_f1.integrations.tum_basic import compare_tum_example
        print(json.dumps(compare_tum_example(args.pit_laps, args.start_compound, args.next_compound), indent=2))
    elif args.command == "llm-smoke":
        from apex_f1.llm import LLMNotConfigured, LLMUpstreamError, smoke_connection

        try:
            print(json.dumps(smoke_connection(), indent=2))
        except (LLMNotConfigured, LLMUpstreamError) as exc:
            parser.exit(1, f"LLM connection test failed: {exc}\n")
    elif args.command == "integrations":
        from apex_f1.integrations.stratlab import probe_stratlab
        from apex_f1.integrations.tum_basic import probe_tum
        print(json.dumps({"tum": probe_tum(), "stratlab": probe_stratlab()}, indent=2))
    elif args.command == "import-race":
        from apex_f1.historical_import import import_to_file
        from apex_f1.replay import HistoricalRace

        target = import_to_file(args.year, args.round, args.output, args.provider)
        summary = HistoricalRace.load(target).summary()
        print(json.dumps({"saved_to": str(target), **summary}, indent=2))
    elif args.command in ("replay-summary", "replay-lap", "replay-report"):
        from apex_f1.historical_import import race_file
        from apex_f1.replay import HistoricalRace

        race = HistoricalRace.load(race_file(args.year, args.round))
        if args.command == "replay-summary":
            result = race.summary()
        elif args.command == "replay-lap":
            result = race.snapshot(args.lap)
        else:
            verification = race.verify_chronology()
            boundaries = race.boundaries()
            picks = sorted({1, max(1, len(boundaries) // 2), len(boundaries)})
            samples = [race.snapshot(int(boundaries[i - 1]["lap"])) for i in picks]
            result = {
                "source": race.source,
                "mode": "HISTORICAL_VERIFICATION_NO_RAW_LAPS",
                "season": race.year,
                "round": race.round_number,
                "completed_lap_records": len(race.laps),
                "driver_count": len({r.driver for r in race.laps}),
                "verification": verification,
                "snapshot_checks": [
                    {
                        "leader_lap": x["as_of_leader_lap"],
                        "cutoff_seconds": x["cutoff_session_seconds"],
                        "visible_record_count": x["n_completed_records_visible"],
                        "visible_driver_count": len(x["drivers"]),
                    }
                    for x in samples
                ],
                "notes": "Retrospective data verification. No race predictions.",
            }
        print(json.dumps(result, indent=2))
    elif args.command == "export-fastf1":
        from apex_f1.fastf1_adapter import export_driver_laps
        target = export_driver_laps(args.year, args.round, args.session, args.driver, args.output)
        print(f"Exported historical laps: {target}")


if __name__ == "__main__":
    main()
