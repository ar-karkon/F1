"""Locate explicitly pinned research submodules without downloading anything."""
from __future__ import annotations

import os
from pathlib import Path


def upstream_dir() -> Path:
    """Override for installations outside the source checkout."""
    override = os.environ.get("APEX_F1_UPSTREAM_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "third_party"


def upstream_path(directory_name: str) -> Path:
    return upstream_dir() / directory_name
