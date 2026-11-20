"""Read-only preflight for pinned F1-StratLab no-LLM model execution.

Never claims actual model execution. Trained artifacts are intentionally not
tracked by the upstream repository; do not substitute dummy weights.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from apex_f1.integrations.paths import upstream_path
from apex_f1.integrations.stratlab import STRATLAB_COMMIT, probe_stratlab

REQUIRED_FILES = (
    "src/strategy/inference/engine.py",
    "src/strategy/inference/no_llm.py",
    "tests/fixtures/mini_race.parquet",
    "data/models/tire_degradation/routing_config.json",
)
MODEL_DIRS = (
    "data/models/lap_time",
    "data/models/agents",
)


def audit_stratlab(root: Path | None = None) -> dict[str, Any]:
    location = root or upstream_path("F1-StratLab")
    source = probe_stratlab(location)
    files = {name: (location / name).is_file() for name in REQUIRED_FILES}
    model_dirs = {name: (location / name).is_dir() for name in MODEL_DIRS}
    try:
        process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=location, text=True, capture_output=True,
            timeout=5, check=False,
        )
        sha = process.stdout.strip() if process.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        sha = None

    pinned = sha == STRATLAB_COMMIT
    missing = [key for key, exists in {**files, **model_dirs}.items() if not exists]
    ready_for_runtime_attempt = (
        source["source_contract_verified"] and pinned and not missing
    )
    if not source["source_present"]:
        status = "NOT_CHECKED_OUT"
    elif not pinned:
        status = "SUBMODULE_SHA_MISMATCH"
    elif missing:
        status = "BLOCKED_MISSING_MODELS_OR_FIXTURES"
    elif source["source_contract_verified"]:
        status = "SOURCE_READY_RUNTIME_UNTESTED"
    else:
        status = "SOURCE_CONTRACT_MISMATCH"

    return {
        "name": "F1-StratLab no-llm",
        "status": status,
        "pinned_commit": STRATLAB_COMMIT,
        "checkout_commit": sha,
        "pinned_checkout_verified": pinned,
        "source_contract_verified": source["source_contract_verified"],
        "required_files_present": files,
        "model_directories_present": model_dirs,
        "missing_prerequisites": missing,
        "runtime_attempt_ready": ready_for_runtime_attempt,
        "runtime_executed": False,
        "actual_model_predictions": False,
        "note": (
            "Original upstream data/models weights are not bundled with its source. "
            "Actual no-llm inference needs legitimate model artifacts and a separate "
            "heavy ML runtime; this check never fabricates inference results."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(audit_stratlab(), indent=2))
