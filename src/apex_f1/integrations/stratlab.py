"""Dependency-free source contract probe for F1-StratLab (not agent execution)."""
from __future__ import annotations

import ast
from pathlib import Path

from apex_f1.integrations.paths import upstream_path

STRATLAB_COMMIT = "b65c34e84c8a9d6e29f7a9741bbaa22b0aae851c"


def probe_stratlab(root: Path | None = None) -> dict:
    """Check that pinned source exports the expected entrypoint via AST parsing.

    This deliberately DOES NOT import transformers, PyTorch, create clients or
    suggest that F1-StratLab can run in the current environment.
    """
    path = (root or upstream_path("F1-StratLab")) / "src/strategy/inference/engine.py"
    result = {
        "name": "F1-StratLab",
        "pinned_commit": STRATLAB_COMMIT,
        "source_present": path.is_file(),
        "entrypoint": "src.strategy.inference.engine.run_lap",
        "source_contract_verified": False,
        "runtime_executed": False,
        "status": "NOT_CHECKED_OUT",
    }
    if not path.is_file():
        return result
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        result["status"] = f"INVALID_SOURCE: {type(exc).__name__}"
        return result
    func = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef)
         and node.name == "run_lap"),
        None,
    )
    names = [] if func is None else [arg.arg for arg in func.args.posonlyargs + func.args.args]
    keywords = [] if func is None else [arg.arg for arg in func.args.kwonlyargs]
    valid = {"race_state", "laps_df"}.issubset(names) and "profile" in keywords
    result["source_contract_verified"] = valid
    result["status"] = "SOURCE_CONTRACT_OK" if valid else "SOURCE_CONTRACT_MISMATCH"
    result["integration_note"] = (
        "Contract-only check. To execute run_lap the separate F1-StratLab environment, "
        "trained artifacts and real session dataframe are required."
    )
    return result
