# Why upstream code is part of the workspace via Git submodules

## Decision (2026-11-20)

Place four high-priority open-source research projects **inside the F1 workspace as pinned Git submodules**, with independent integration adapters under `src/apex_f1/`. The core simulator remains independently testable.

```text
F1/
  src/apex_f1/                     Our own MIT-licensed application
  tests/                           Application tests
  third_party/
    race-simulation/               Git submodule → TUM (LGPL-3.0)
    F1-StratLab/                    Git submodule → F1-StratLab (Apache-2.0)
    Pit-Wall-F1-Project/           Git submodule → Pit Wall (MIT)
    motorsport-analytics-pipeline/ Git submodule → analytics (MIT)
  .gitmodules                      Upstream URLs and checkout locations
  docs/                            Technical design and validation
```

### Why submodules first?

- Keep a single workspace where the team can inspect or execute upstream code.
- Avoid copying unrelated large projects into every F1 source commit.
- Respect upstream git history and retain provenance with pinned SHA.
- Prevent accidental updates from destabilizing the main app.
- Leave clean space for adapters, benchmark tests and a later focused integration.

### What does **not** happen automatically?

- A normal `git clone` downloads Git pointers, **not full submodule contents**; use `git clone --recurse-submodules` or `git submodule update --init`.
- Editing a submodule does not push changes to upstream. For custom changes, create a fork under an account with write access and change the recorded URL, or migrate carefully via a reviewed Git subtree.
- Importing source does not imply the projects are compatible, executable together or deployed.
- The OpenF1 API's data terms are separate from the repo code license.

### When to switch to a subtree or vendor only selected code?

If a particular upstream tool becomes core to Apex's product and needs frequent modifications, prefer a **reviewed and pinned git subtree** (source genuinely stored in the F1 repository) or a separately maintained fork. Do not subtree the entire research stack before benchmarking it. An LGPL component needs a deliberate compliance review for the intended integration and distribution.

### Next milestone

Create versioned adapters with smoke tests for TUM simulation and telemetry pipeline, and benchmark outputs against the existing toy baseline before promoting any recommendation to model-backed status.
