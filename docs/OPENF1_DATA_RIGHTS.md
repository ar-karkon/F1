# OpenF1 historical source: access and licensing

API reference: https://openf1.org/docs/
Current project terms: https://openf1.org/

- Historical data from 2023 onward is accessible without authentication.
- Public historical access is provided for education, personal projects,
  academic research and non-commercial fan engagement.
- **Do not assume commercial redistribution, sublicensing, customer-facing
  resale or production team use is permitted without separately clearing
  rights with the provider and relevant data rights-holders.**
- We do not commit complete OpenF1 / FastF1 timing dumps or cache files.
- The project stores the selected race as a gitignored local replay snapshot.
- GitHub Actions uploads only a small derived verification report for debugging.
- The importer uses only historical race sessions, not paid/live endpoints.

## Data quality and limitations

OpenF1 lap `date_start` is **approximate**, so `date_start + lap_duration`
produces an *approximate completion timestamp*. If a lap has no duration,
the next lap's start is used only to infer the preceding lap's completion.
There is no physical track position between completed laps.

Tyre joins use only `stints.lap_start`, not `lap_end` (the latter reveals
how a stint finished). Position joins use only events timestamped at/before
lap completion, and pit events are marked only if their timestamp is before
lap completion. These are *historically reconstructed* joins, not proof
that every original source field was published immediately in real time.

For an engineering-grade timing source, secure an approved live feed and
field-level release-timestamp audit before training an agent or claiming
no operational data leakage.
