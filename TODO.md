# TODO - TrendScope next-level prediction foundation

## Step 1 — Historical snapshots + DB (Google-only MVP)
- [x] Add SQLite storage module: `src/storage/snapshots_db.py`

  - Tables for snapshot runs and per-keyword momentum rows
- [x] Add snapshot runner module: `src/pipeline/snapshot_runner.py`

  - Fetch Google trends (reusing existing scrapers)
  - Convert wide→long and compute momentum
  - Persist raw snapshot metadata + momentum rows into SQLite
- [x] Add API endpoints in `src/api/main.py`

  - `POST /api/snapshots/run_google`
  - `GET /api/training/google_momentum`

## Step 2 — Validate snapshot storage
- [x] Run snapshot once via API

- [x] Confirm `/api/training/google_momentum` returns historical rows


## Step 3 — ML baseline model (Google-only spike prediction)
- [ ] Define label (spike) from future momentum horizon
- [ ] Implement training script (logistic regression / gradient boosting)
- [ ] Add `GET /api/predictions/google_spike` endpoint


