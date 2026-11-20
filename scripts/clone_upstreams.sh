#!/usr/bin/env bash
# Compatibility command: fetch the four pinned Git submodules into third_party/.
set -euo pipefail
if [[ ! -f .gitmodules ]]; then
  echo "Run from the F1 repository root (missing .gitmodules)" >&2
  exit 1
fi
git submodule update --init
echo "Pinned upstream research repositories checked out under third_party/."
echo "They are not yet integrated into the Apex Intelligence runtime."
