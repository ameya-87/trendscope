"""Training entrypoint for Google spike predictor (MVP).

Usage (example):
  python -m src.ml.train_google_spike --keywords AI,Bitcoin --delta 1.0

This writes model file into reports/predictions/.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime

from src.config.settings import config
from src.ml.google_spike_model import save_models, train_google_spike_models
from src.storage.snapshots_db import get_default_db


def _parse_keywords(s: str | None) -> list[str] | None:
    if not s:
        return None
    return [x.strip() for x in s.split(",") if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", type=str, default=None, help="Comma-separated list of keywords")
    ap.add_argument("--delta", type=float, default=1.0)
    ap.add_argument("--out", type=str, default=None, help="Optional output model path")
    args = ap.parse_args()

    keywords = _parse_keywords(args.keywords)
    if keywords is None:
        keywords = [k.strip() for k in config.KEYWORDS.split(",") if k.strip()]

    db = get_default_db()

    models = train_google_spike_models(db=db, keywords=keywords, delta=float(args.delta))

    out_dir = os.path.join("reports", "predictions")
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.out
    if not out_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(out_dir, f"google_spike_models_delta{args.delta}_{ts}.joblib")

    save_models(models, out_path=out_path)
    print(f"Saved {len(models)} keyword models -> {out_path}")


if __name__ == "__main__":
    main()

