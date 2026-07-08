import os
import glob
from datetime import datetime
from typing import List
import pandas as pd

from src.processing.text_cleaning import clean_dataframe
from src.analysis.trend_detection import process_raw_trends


UNIFIED_COLUMNS = [
    "source", "published_at", "keyword", "title", "text", "url", "author", "views", "likes", "comments", "cleaned_text"
]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_read_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        # Return empty DF on read errors to keep pipeline resilient
        return pd.DataFrame(columns=UNIFIED_COLUMNS)


def _ensure_unified_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in UNIFIED_COLUMNS:
        if col not in out.columns:
            out[col] = None
    # Ensure 'cleaned_text' is always the last column if it exists
    if "cleaned_text" in out.columns and "cleaned_text" in UNIFIED_COLUMNS:
        unified_cols_ordered = [col for col in UNIFIED_COLUMNS if col != "cleaned_text"] + ["cleaned_text"]
        return out[unified_cols_ordered]
    return out[UNIFIED_COLUMNS]


def prepare_social_posts_export(raw_dir: str = os.path.join("data", "raw"), output_dir: str = os.path.join("reports", "powerbi")) -> str:
    """
    Combine latest social CSVs (YouTube, Reddit, Twitter) into a unified export for Power BI.
    Adds a cleaned_text column using the text cleaning utility.
    """
    _ensure_dir(output_dir)

    social_patterns = [
        os.path.join(raw_dir, "youtube_*.csv"),
        os.path.join(raw_dir, "reddit_*.csv"),
        os.path.join(raw_dir, "twitter_*.csv"),
        os.path.join(raw_dir, "tvmaze_*.csv"),
    ]

    frames: List[pd.DataFrame] = []
    for pattern in social_patterns:
        for path in glob.glob(pattern):
            df = _safe_read_csv(path)
            df = _ensure_unified_columns(df)
            frames.append(df)

    if frames:
        combined = pd.concat(frames, ignore_index=True)
    else:
        combined = pd.DataFrame(columns=UNIFIED_COLUMNS)



    out_path = os.path.join(output_dir, f"social_posts_{_timestamp()}.csv")
    combined.to_csv(out_path, index=False)
    return out_path


def _find_latest(path_glob: str) -> str | None:
    files = glob.glob(path_glob)
    if not files:
        return None
    return sorted(files)[-1]


def prepare_trends_export(processed_dir: str = os.path.join("data", "processed"), raw_dir: str = os.path.join("data", "raw"), output_dir: str = os.path.join("reports", "powerbi")) -> str:
    """
    Copy or generate trends momentum CSV for Power BI export.
    If a processed momentum file exists, copy the latest; otherwise, process the latest raw Google Trends CSV.
    """
    _ensure_dir(output_dir)

    latest_momentum = _find_latest(os.path.join(processed_dir, "trends_momentum_*.csv"))
    if latest_momentum and os.path.isfile(latest_momentum):
        df = pd.read_csv(latest_momentum)
    else:
        latest_raw = _find_latest(os.path.join(raw_dir, "google_trends_*.csv"))
        if not latest_raw:
            # No raw data; return an empty CSV with expected columns
            df = pd.DataFrame(columns=["keyword", "latest_value", "momentum", "last_date", "trend_direction"])
        else:
            out_path = process_raw_trends(latest_raw)
            df = pd.read_csv(out_path)

    out_path = os.path.join(output_dir, f"trends_momentum_{_timestamp()}.csv")
    df.to_csv(out_path, index=False)
    return out_path


def export_for_powerbi() -> tuple[str, str]:
    """
    Run both social posts and trends momentum exports.
    Returns (social_csv_path, trends_csv_path).
    """
    social_csv = prepare_social_posts_export()
    trends_csv = prepare_trends_export()
    print(f"✅ Power BI social export: {social_csv}")
    print(f"✅ Power BI trends export: {trends_csv}")
    return social_csv, trends_csv


if __name__ == "__main__":
    export_for_powerbi()