#!/usr/bin/env bash
# Optional research checkouts; intentionally not part of the main codebase.
set -euo pipefail
mkdir -p external
clone_if_missing() {
  local repo="$1" target="$2"
  if [[ -d "$target/.git" ]]; then
    echo "Already cloned: $target"
  elif [[ -e "$target" ]]; then
    echo "Refusing to overwrite existing path: $target" >&2
    exit 1
  else
    git clone --depth 1 "$repo" "$target"
  fi
}
clone_if_missing https://github.com/TUMFTM/race-simulation.git external/race-simulation
clone_if_missing https://github.com/VforVitorio/F1-StratLab.git external/F1-StratLab
clone_if_missing https://github.com/MarcGuitart/Pit-Wall-F1-Project.git external/Pit-Wall-F1-Project
echo "Research checkouts complete. Review each upstream license before code integration."
