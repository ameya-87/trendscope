"""SQLite storage for TrendScope historical snapshots.

MVP scope: Google Trends snapshots + per-keyword momentum rows.

This module is intentionally lightweight (single-file SQLite, no ORM)
so it works out-of-the-box for local experimentation.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class SnapshotRun:
    snapshot_id: int
    created_at_utc: str
    source: str
    timeframe: str | None
    geo: str | None
    lookback: int
    keywords_csv: str


class SnapshotsDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        Path(os.path.dirname(self.db_path)).mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")

            # Snapshot metadata
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshot_runs (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at_utc TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timeframe TEXT,
                    geo TEXT,
                    lookback INTEGER NOT NULL,
                    keywords_csv TEXT NOT NULL
                );
                """
            )

            # Raw artifacts (we keep just the path + minimal metadata)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshot_artifacts (
                    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL REFERENCES snapshot_runs(snapshot_id),
                    artifact_type TEXT NOT NULL,
                    file_path TEXT,
                    created_at_utc TEXT NOT NULL
                );
                """
            )

            # Keyword-level momentum rows.
            # We store a consistent feature target that can later be used for ML.
            # Note: momentum in the current code is not persisted as “time series”
            # but as a point-in-time score derived from the raw time series.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS keyword_momentum (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL REFERENCES snapshot_runs(snapshot_id),
                    keyword TEXT NOT NULL,
                    latest_value REAL,
                    momentum REAL,
                    last_date TEXT,
                    trend_direction TEXT
                );
                """
            )

            conn.commit()

    def create_google_snapshot(
        self,
        *,
        timeframe: str | None,
        geo: str | None,
        lookback: int,
        keywords: Iterable[str],
    ) -> int:
        keywords_list = [k.strip() for k in keywords if str(k).strip()]
        created_at = datetime.utcnow().isoformat() + "Z"
        keywords_csv = ",".join(keywords_list)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO snapshot_runs (created_at_utc, source, timeframe, geo, lookback, keywords_csv)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (created_at, "google_trends", timeframe, geo, int(lookback), keywords_csv),
            )
            conn.commit()
            return int(cur.lastrowid)

    def add_artifact(
        self,
        snapshot_id: int,
        *,
        artifact_type: str,
        file_path: str | None,
    ) -> None:
        created_at = datetime.utcnow().isoformat() + "Z"
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO snapshot_artifacts (snapshot_id, artifact_type, file_path, created_at_utc)
                VALUES (?, ?, ?, ?)
                """,
                (int(snapshot_id), artifact_type, file_path, created_at),
            )
            conn.commit()

    def insert_keyword_momentum_rows(
        self,
        snapshot_id: int,
        rows: list[dict[str, Any]],
    ) -> int:
        """rows should contain keys: keyword, latest_value, momentum, last_date, trend_direction"""
        if not rows:
            return 0
        with self._lock, self._connect() as conn:
            cur = conn.cursor()
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO keyword_momentum (snapshot_id, keyword, latest_value, momentum, last_date, trend_direction)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(snapshot_id),
                        str(r.get("keyword", "")),
                        None if r.get("latest_value") is None else float(r.get("latest_value")),
                        None if r.get("momentum") is None else float(r.get("momentum")),
                        None if not r.get("last_date") else str(r.get("last_date")),
                        str(r.get("trend_direction") or "flat"),
                    ),
                )
            conn.commit()
            return len(rows)

    def list_keyword_momentum_for_keyword(
        self,
        *,
        keyword: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                SELECT
                    sr.snapshot_id,
                    sr.created_at_utc,
                    sr.source,
                    sr.timeframe,
                    sr.geo,
                    sr.lookback,
                    km.keyword,
                    km.latest_value,
                    km.momentum,
                    km.last_date,
                    km.trend_direction
                FROM snapshot_runs sr
                JOIN keyword_momentum km ON km.snapshot_id = sr.snapshot_id
                WHERE sr.source = 'google_trends' AND km.keyword = ?
                ORDER BY sr.snapshot_id DESC
                LIMIT ?
                """,
                (keyword, int(limit)),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def list_google_training_rows(
        self,
        *,
        keyword: str | None,
        from_snapshot_id: int | None,
        to_snapshot_id: int | None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        where = ["sr.source = 'google_trends'"]
        params: list[Any] = []
        if keyword:
            where.append("km.keyword = ?")
            params.append(keyword)
        if from_snapshot_id is not None:
            where.append("sr.snapshot_id >= ?")
            params.append(int(from_snapshot_id))
        if to_snapshot_id is not None:
            where.append("sr.snapshot_id <= ?")
            params.append(int(to_snapshot_id))

        where_sql = " AND ".join(where)
        q = f"""
            SELECT
                sr.snapshot_id,
                sr.created_at_utc,
                sr.source,
                sr.timeframe,
                sr.geo,
                sr.lookback,
                km.keyword,
                km.latest_value,
                km.momentum,
                km.last_date,
                km.trend_direction
            FROM snapshot_runs sr
            JOIN keyword_momentum km ON km.snapshot_id = sr.snapshot_id
            WHERE {where_sql}
            ORDER BY sr.snapshot_id DESC
            LIMIT ?
        """
        params.append(int(limit))
        with self._lock, self._connect() as conn:
            cur = conn.execute(q, params)
            return [dict(r) for r in cur.fetchall()]


def get_default_db() -> SnapshotsDB:
    root = Path(__file__).resolve().parents[2]
    db_path = root / "data" / "training" / "trendscope.sqlite"
    return SnapshotsDB(str(db_path))

