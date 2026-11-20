# FastF1 historical replay — completed lap data, strict as-of cutoffs

## What is implemented

A historical importer and read-only race replay mode. Each snapshot at leader
lap **N** uses the earliest observed session completion time for lap N and
exposes only driver laps which have completed by that exact session timestamp.

**Important:** Filtering merely by `LapNumber <= N` is incorrect because a
car behind the leader can complete its Nth lap later. This implementation
filters by `Time <= leader completion time`, then selects each driver's latest
completed lap. `Position` in the returned driver card is the **last reported**
position, not a claim of a synchronized live classification.

This is a retrospective based on completed-lap timing; the source can include
post-race corrections. Do not present it as genuine low-latency live timing.

## Fetch one historic race (explicit network action)

```bash
git clone https://github.com/ar-karkon/F1.git
cd F1
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,data]"
apex-f1 import-race --year 2024 --round 1
apex-f1 replay-summary --year 2024 --round 1
apex-f1 replay-lap --year 2024 --round 1 --lap 17
apex-f1 serve
```

Open `http://localhost:8000/replay`. Import runs only through CLI; the
browser/API never downloads races itself. Data is saved to an ignored
`data/derived/race-2024-round-1-R.json` file, not committed to Git.
FastF1 uses `data/cache/fastf1` for its HTTP cache.

### API

- `GET /api/v1/historical/2024/1/summary` — retrospective full-session index (includes later laps).
- `GET /api/v1/historical/2024/1/snapshot/17` — only rows completed before cutoff at leader lap 17.
- `GET /replay` — local replay UI with lap scrubber and driver cards.

The summary endpoint is **not** a predictor input: it includes the full session.
Models making decisions at lap N must only receive the `snapshot/N` response,
never the full session JSON or summary. A snapshot is not a real-time feed
and not a trained prediction.

### Reproducible live-source smoke test

A separate GitHub Actions job imports 2024 Bahrain (round 1), saves only
a small **derived verification report**, and uploads it as a temporary artifact.
Raw race laps and FastF1 cache are not uploaded or committed. Real-data
ingestion is a network-dependent optional check, distinct from offline CI.
GitHub may rate-limit or block upstream sources; errors must not silently
fall back to fabricated data.

## Current limitations

- Session R only; no realtime SC/radio/weather, telemetry or rival positions
  between completed laps.
- Some rows may be absent due to invalid or missing session timestamps.
- TyreLife may reflect post-processed values: **as-of row cutoff does not
  guarantee every field was publicly known during the live broadcast**.
  For strict live-equivalent studies, drop fields without a disclosure guarantee.
- No 2026 regulations, engineer decision recommendation, or pit simulation
  based on this historical feed yet.
- Race results/ground truth must remain separate from model input snapshots.

## License and provenance

FastF1's software license does not automatically grant redistribution rights
for underlying commercial F1 timing information. Keep raw imports local and
review applicable source terms before publishing datasets.
