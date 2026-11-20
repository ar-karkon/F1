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


## Pit timestamp mapping and out-lap proxy (model v2)

A race-data audit on 2024 Japan found 54 entries in the OpenF1 `pit`
endpoint and 54 flags in `laps.is_pit_out_lap`, but the old mapping to a
same-numbered lap only preserved 18 as completed-lap `pit_in` events.
The pit API's `lap_number` should **not** be assumed to designate a
completed lap whose end timestamp is after the pit event.

The importer now sorts pit event timestamps per driver and makes each
passage visible only at the first subsequently **completed** driver lap.
This avoids backdating an event to a completion that occurred before it.
Pit events after a driver's last usable completion remain unassigned.

For the independent *Opponent Pit Window* empirical benchmark, labels
intentionally use `laps.is_pit_out_lap` (excluding race lap 1) as a more
directly observable historical proxy for pit lane activity. An out-lap does
not distinguish a strategic tyre change from red flags, drive-throughs or
pit-lane starts, so the benchmark does not establish a model of pit intent.
