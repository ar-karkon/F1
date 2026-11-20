# Upstream open-source project inventory

External projects below were reviewed at the repository-metadata level on 2026-11-20. They are **not bundled, forked, integrated, or executed by this repo**. Their original copyright, license, and ownership remain with upstream authors.

| Project | Repository | License | Potential role | Decision |
| --- | --- | --- | --- | --- |
| TUM Race Simulation | https://github.com/TUMFTM/race-simulation | LGPL-3.0 | Research-grade race strategy simulator | Optional cloned checkout; assess dependencies and linking obligations |
| F1-StratLab | https://github.com/VforVitorio/F1-StratLab | Apache-2.0 | Multi-agent strategy/replay patterns | Reference only; main branch under development |
| Pit Wall Engineer | https://github.com/MarcGuitart/Pit-Wall-F1-Project | MIT | Dashboards and telemetry architecture | Reference only |
| Motorsport Analytics Pipeline | https://github.com/ElSirGuti/motorsport-analytics-pipeline | MIT | Driver telemetry analysis, CSV input | Potential later adapter |
| FastF1 | https://github.com/theOehrly/Fast-F1 | MIT | Historic laps and timing | Optional package dependency for export |
| OpenF1 | https://github.com/br-g/openf1 | Verify upstream license/terms | Historic and live API | Not bundled; API usage requires separate terms review |
| Jolpica F1 | https://github.com/jolpica/jolpica-f1 | Apache-2.0 | Historical race results | Future adapter |
| F1 Strategy Engine | https://github.com/LoreMonti/F1-strategy-engine | MIT | Monte Carlo examples | Reference only |

## Cloning references

`bash scripts/clone_upstreams.sh` clones TUM, F1-StratLab and Pit Wall Engineer to `external/`. These are intentionally ignored in Git because a shared codebase is **not** a reason to copy large unrelated repos or erase their history.

## Before integrating source code

1. Confirm the **exact** upstream license, notices, code provenance, and project maintenance.
2. Pin a commit SHA; review security, external services, requirements and license compatibility.
3. Prefer documented interfaces or independent adapters over copying entire project trees.
4. Retain required notices, attribution and source availability conditions (particularly LGPL).
5. Keep data usage terms separate from software code licenses.
6. Add a contract test and measured benefit before introducing a heavyweight dependency.

The independent Apex Intelligence source in this repo uses MIT; this does not relicense upstream libraries or their data.
