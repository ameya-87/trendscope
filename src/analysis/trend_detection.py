import os
import pandas as pd
import numpy as np
from datetime import datetime


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_raw_trends(csv_path: str) -> pd.DataFrame:
    """
    Load a raw Google Trends CSV produced by pytrends.interest_over_time().
    Expects an index column named 'date' saved as a CSV column.
    """
    df = pd.read_csv(csv_path, parse_dates=["date"])
    # Ensure sorted by date
    if "date" in df.columns:
        df = df.sort_values("date")
    return df


def wide_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert wide format (date + one column per keyword) to long format.
    Output columns: date, keyword, score
    """
    if "date" not in df.columns:
        raise ValueError("Input DataFrame must contain a 'date' column.")
    value_cols = [c for c in df.columns if c != "date"]
    long_df = df.melt(id_vars=["date"], value_vars=value_cols, var_name="keyword", value_name="score")
    return long_df


def compute_keyword_momentum(long_df: pd.DataFrame, lookback: int = 4) -> pd.DataFrame:
    """
    Compute a simple momentum score per keyword: last value minus mean of the previous (lookback-1) values.
    - lookback: total points considered including the last point. Default 4 -> previous 3 as baseline.
    Returns a summary DataFrame with columns:
      keyword, latest_value, momentum, last_date, trend_direction
    """
    summaries = []
    for kw, grp in long_df.groupby("keyword"):
        grp = grp.sort_values("date")
        values = grp["score"].astype(float).values
        dates = grp["date"].values
        if len(values) < lookback:
            latest_value = values[-1] if len(values) > 0 else np.nan
            momentum = np.nan
            direction = "flat"
        else:
            latest_value = values[-1]
            baseline = np.mean(values[-(lookback): -1])  # previous lookback-1 points
            momentum = latest_value - baseline
            if np.isnan(momentum) or momentum == 0:
                direction = "flat"
            elif momentum > 0:
                direction = "up"
            else:
                direction = "down"
        summaries.append({
            "keyword": kw,
            "latest_value": latest_value,
            "momentum": momentum,
            "last_date": pd.Timestamp(dates[-1]) if len(dates) > 0 else pd.NaT,
            "trend_direction": direction,
        })
    return pd.DataFrame(summaries)


def process_raw_trends(input_csv_path: str, output_csv_path: str | None = None, lookback: int = 4) -> str:
    """
    End-to-end processing for Google Trends raw CSV:
      1) Load raw CSV
      2) Convert to long format
      3) Compute momentum per keyword
      4) Save processed summary CSV to data/processed (or provided path)
    Returns the path to the processed CSV.
    """
    df = load_raw_trends(input_csv_path)
    long_df = wide_to_long(df)
    summary_df = compute_keyword_momentum(long_df, lookback=lookback)

    if output_csv_path is None:
        _ensure_dir(os.path.join("data", "processed"))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv_path = os.path.join("data", "processed", f"trends_momentum_{ts}.csv")

    summary_df.to_csv(output_csv_path, index=False)
    return output_csv_path


if __name__ == "__main__":
    # Attempt to find the latest raw Google Trends file and process it.
    raw_dir = os.path.join("data", "raw")
    if not os.path.isdir(raw_dir):
        raise SystemExit("data/raw directory not found. Run the scraper first.")

    candidates = [f for f in os.listdir(raw_dir) if f.startswith("google_trends_") and f.endswith(".csv")]
    if not candidates:
        raise SystemExit("No google_trends_*.csv found in data/raw. Run the scraper first.")

    latest = sorted(candidates)[-1]
    input_csv = os.path.join(raw_dir, latest)
    out_path = process_raw_trends(input_csv)
    print(f"✅ Processed momentum saved to {out_path}")