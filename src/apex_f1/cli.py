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

    status = subparsers.add_parser("integrations", help="Inspect pinned upstream source readiness")

    args = parser.parse_args()
    if args.command == "demo":
        print(json.dumps(evaluate_strategies(RaceState(), args.trials, args.seed), indent=2))
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("apex_f1.api:app", host=args.host, port=args.port)
    elif args.command == "tum-compare":
        from apex_f1.integrations.tum_basic import compare_tum_example
        print(json.dumps(compare_tum_example(args.pit_laps, args.start_compound, args.next_compound), indent=2))
    elif args.command == "integrations":
        from apex_f1.integrations.stratlab import probe_stratlab
        from apex_f1.integrations.tum_basic import probe_tum
        print(json.dumps({"tum": probe_tum(), "stratlab": probe_stratlab()}, indent=2))
    elif args.command == "export-fastf1":
        from apex_f1.fastf1_adapter import export_driver_laps
        target = export_driver_laps(args.year, args.round, args.session, args.driver, args.output)
        print(f"Exported historical laps: {target}")


if __name__ == "__main__":
    main()
