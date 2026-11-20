# Open-source research repositories included as pinned Git submodules

Reviewed repository metadata: 2026-11-20. Four projects are **tracked** as Git submodules at immutable revision SHAs. They are not vendored copies, forks, or currently running components. Their original license, notices, copyright, and upstream ownership remain unchanged.

| Project | In F1 repository | Upstream source | Commit pinned | License | Proposed use |
| --- | --- | --- | --- | --- | --- |
| TUM Race Simulation | `third_party/race-simulation` | https://github.com/TUMFTM/race-simulation | `96ef2c202198` | LGPL-3.0 | Race strategy / simulation, with license and dependency assessment |
| F1-StratLab | `third_party/F1-StratLab` | https://github.com/VforVitorio/F1-StratLab | `b65c34e84c8a` | Apache-2.0 | Multi-agent orchestration and replay patterns; upstream active development |
| Pit Wall Engineer | `third_party/Pit-Wall-F1-Project` | https://github.com/MarcGuitart/Pit-Wall-F1-Project | `070594892dd7` | MIT | Race engineering UI and telemetry techniques |
| Motorsport Analytics Pipeline | `third_party/motorsport-analytics-pipeline` | https://github.com/ElSirGuti/motorsport-analytics-pipeline | `f47d319ed6e9` | MIT | Driver telemetry, CSV ingest and analysis |

Additional tools/packages **not** tracked as Git submodules:

| Package / service | Repository | License / rights | Status |
| --- | --- | --- | --- |
| FastF1 | https://github.com/theOehrly/Fast-F1 | MIT | Optional Python dependency through `pip install -e ".[data]"` |
| OpenF1 | https://github.com/br-g/openf1 | Verify upstream license and API data-use terms | External API to consider |
| Jolpica F1 | https://github.com/jolpica/jolpica-f1 | Apache-2.0 | External API to consider |
| F1 Strategy Engine | https://github.com/LoreMonti/F1-strategy-engine | MIT | Research reference; not integrated |

## Download pinned source

```bash
git clone --recurse-submodules https://github.com/ar-karkon/F1.git
# Existing checkout:
git submodule update --init
# Compatibility helper:
bash scripts/clone_upstreams.sh
```

Git automatically checks out each recorded commit, even if the upstream default branch changes. For nested upstream submodules, review their license and dependency tree first, then choose whether to initialize recursively. This repository does **not** pull every nested upstream component by default.

## Important ownership distinction

A submodule **points to a separate upstream repository**; it does *not* copy its full source history into F1. GitHub displays the linked path, and a `--recurse-submodules` clone gives you its source in the F1 working directory. A fork plus submodule permits independent modifications; a Git subtree actually embeds code in F1 with separate license obligations. See [repository strategy](REPOSITORY_STRATEGY.md).

## Integration policy

1. Keep original notices and respect each project license, especially LGPL-3.0 requirements.
2. Run and benchmark any upstream component **in isolation** before using it in an application.
3. Integrate through versioned adapters in `src/apex_f1/`, not direct unreviewed changes inside upstream code.
4. Do not imply externally supplied source is originally authored by Apex.
5. Confirm research code's security posture, data rights, dependency compatibility, and 2026 race-rule limitations.
6. Update pinned commits deliberately with an integration test and PR, never automatically track mutable upstream heads.

Independent Apex code uses MIT. **MIT does not relicense third-party source or datasets.**
