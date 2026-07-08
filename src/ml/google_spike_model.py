"""Google momentum spike model (Google-only MVP).

MVP goal:
- Train a simple classifier to predict probability that momentum will spike
  in the *next snapshot*.

Training data source:
- SQLite rows from `keyword_momentum` table populated by snapshot runner.

Label definition:
- spike=1 if (momentum_{t+1} - momentum_t) >= delta else 0

Features (minimal MVP):
- momentum_t
- latest_value_t
- trend_direction_t (encoded)

Model:
- Logistic Regression

The module provides:
- train_google_spike_model(db, keyword_filter=None)
- predict_google_spike(model, current_rows)

For a first MVP, this is intentionally light-weight.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression





from src.storage.snapshots_db import SnapshotsDB, get_default_db


@dataclass(frozen=True)
class GoogleSpikeConfig:
    delta: float = 1.0


def _encode_direction(d: str | None) -> float:
    if not d:
        return 0.0
    d = d.lower().strip()
    if d == "up":
        return 1.0
    if d == "down":
        return -1.0
    return 0.0


def _rows_to_feature_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Ensure ordering by snapshot_id asc
    if "snapshot_id" in df.columns:
        df = df.sort_values("snapshot_id")

    # Normalize expected columns
    df["momentum_t"] = pd.to_numeric(df.get("momentum"), errors="coerce")
    df["latest_value_t"] = pd.to_numeric(df.get("latest_value"), errors="coerce")
    df["dir_t"] = df.get("trend_direction").map(_encode_direction).astype(float)

    return df[["snapshot_id", "created_at_utc", "momentum_t", "latest_value_t", "dir_t"]]


def _make_supervised_examples(df: pd.DataFrame, *, delta: float) -> tuple[np.ndarray, np.ndarray]:
    """Create X_t and y_t using next-row momentum delta."""
    if df.shape[0] < 3:
        return np.empty((0, 3)), np.empty((0,))

    # next momentum
    momentum = df["momentum_t"].values.astype(float)
    latest = df["latest_value_t"].values.astype(float)
    direction = df["dir_t"].values.astype(float)

    X = np.vstack([momentum[:-1], latest[:-1], direction[:-1]]).T
    y = (momentum[1:] - momentum[:-1] >= float(delta)).astype(int)

    return X, y


@dataclass
class TrainedGoogleSpikeModel:
    keyword: str
    delta: float
    model: LogisticRegression
    trained_on_rows: int


def train_google_spike_model_for_keyword(
    *,
    db: SnapshotsDB,
    keyword: str,
    delta: float = 1.0,
) -> TrainedGoogleSpikeModel | None:
    rows = db.list_keyword_momentum_for_keyword(keyword=keyword, limit=5000)
    if len(rows) < 10:
        return None

    df = _rows_to_feature_df(rows)
    X, y = _make_supervised_examples(df, delta=delta)

    # Need both classes
    if X.shape[0] < 10 or len(set(y.tolist())) < 2:
        return None

    # Basic logistic regression (default regularization)
    clf = LogisticRegression(max_iter=2000)
    clf.fit(X, y)

    return TrainedGoogleSpikeModel(keyword=keyword, delta=delta, model=clf, trained_on_rows=int(X.shape[0]))


def train_google_spike_models(
    *,
    db: SnapshotsDB | None = None,
    keywords: Iterable[str] | None = None,
    delta: float = 1.0,
    min_rows: int = 10,
) -> dict[str, TrainedGoogleSpikeModel]:
    db = db or get_default_db()

    if keywords is None:
        # derive keyword list from DB: simple brute force
        # For MVP, we just rely on a user-provided list; otherwise we would need a SQL query.
        raise ValueError("For MVP, provide `keywords` to train explicitly.")

    out: dict[str, TrainedGoogleSpikeModel] = {}
    for kw in keywords:
        try:
            tm = train_google_spike_model_for_keyword(db=db, keyword=str(kw), delta=delta)
            if tm is not None and tm.trained_on_rows >= min_rows:
                out[str(kw)] = tm
        except Exception:
            continue
    return out


def save_models(models: dict[str, TrainedGoogleSpikeModel], *, out_path: str) -> None:
    # Use pickle to avoid depending on joblib (faster + fewer deps).
    payload = {

        kw: {
            "keyword": m.keyword,
            "delta": m.delta,
            "trained_on_rows": m.trained_on_rows,
            "model": m.model,
        }
        for kw, m in models.items()
    }
    with open(out_path, 'wb') as f:
        pickle.dump(payload, f)



def load_models(in_path: str) -> dict[str, dict[str, Any]]:
    with open(in_path, 'rb') as f:
        return pickle.load(f)



def predict_google_spike_probability(
    *,
    trained: dict[str, Any],
    latest_rows: list[dict[str, Any]],
) -> float | None:
    """Predict using the most recent row as X_t."""
    if not latest_rows:
        return None

    # Sort by snapshot_id asc and take last
    df = _rows_to_feature_df(latest_rows)
    df = df.sort_values("snapshot_id")
    last = df.iloc[-1]

    X = np.array([[float(last["momentum_t"]), float(last["latest_value_t"]), float(last["dir_t"])]])
    proba = trained["model"].predict_proba(X)[0]
    # class 1 probability
    return float(proba[1])

