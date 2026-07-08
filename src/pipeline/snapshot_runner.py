"""Snapshot runner for TrendScope.

MVP scope:
- Fetch Google Trends for configured keywords
- Compute momentum summary per keyword
- Persist snapshot metadata and keyword momentum rows into SQLite

Later we’ll expand this pattern to other sources.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import pandas as pd

from src.analysis.trend_detection import compute_keyword_momentum, wide_to_long
from src.config.settings import config
from src.scraping.google_trends_scraper import fetch_trends
from src.storage.snapshots_db import SnapshotsDB, get_default_db


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


@dataclass(frozen=True)
class GoogleSnapshotRequest:
    timeframe: str = "now 7-d"
    geo: str = ""
    lookback: int = 4
    keywords: list[str] | None = None


def run_google_snapshot(req: GoogleSnapshotRequest | None = None, *, db: SnapshotsDB | None = None) -> int:
    req = req or GoogleSnapshotRequest()
    db = db or get_default_db()

    keywords = req.keywords if req.keywords is not None else [k.strip() for k in config.KEYWORDS.split(",") if k.strip()]
    if not keywords:
        raise ValueError("No keywords provided for snapshot")

    snapshot_id = db.create_google_snapshot(
        timeframe=req.timeframe,
        geo=req.geo,
        lookback=req.lookback,
        keywords=keywords,
    )

    # Persist raw time series snapshot as artifact
    raw_df = fetch_trends(keywords, timeframe=req.timeframe, geo=req.geo)
    if raw_df is None or getattr(raw_df, "empty", True):
        # Save still the snapshot metadata; no momentum rows.
        return snapshot_id

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_out_dir = os.path.join("data", "raw")
    _ensure_dir(raw_out_dir)
    raw_path = os.path.join(raw_out_dir, f"google_trends_{ts}.csv")

    # This CSV is expected by trend_detection.load_raw_trends (it parses 'date').
    out_df = raw_df.reset_index()
    out_df.to_csv(raw_path, index=False)
    db.add_artifact(snapshot_id, artifact_type="google_trends_raw_csv", file_path=raw_path)

    # Compute momentum from the in-memory raw DF too (avoid reading CSV again)
    long_df = wide_to_long(out_df)
    summary_df = compute_keyword_momentum(long_df, lookback=req.lookback)

    rows = summary_df.to_dict(orient="records") if isinstance(summary_df, pd.DataFrame) else []
    db.insert_keyword_momentum_rows(snapshot_id, rows)
    return snapshot_id


if __name__ == "__main__":
    sid = run_google_snapshot()
    print(f"Saved Google snapshot: {sid}")

