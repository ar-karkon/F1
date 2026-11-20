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

    args = parser.parse_args()
    if args.command == "demo":
        print(json.dumps(evaluate_strategies(RaceState(), args.trials, args.seed), indent=2))
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("apex_f1.api:app", host=args.host, port=args.port)
    elif args.command == "export-fastf1":
        from apex_f1.fastf1_adapter import export_driver_laps
        target = export_driver_laps(args.year, args.round, args.session, args.driver, args.output)
        print(f"Exported historical laps: {target}")


if __name__ == "__main__":
    main()
