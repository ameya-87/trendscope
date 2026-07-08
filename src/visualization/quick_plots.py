import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def plot_trends_time_series(raw_csv_path: str, output_svg_path: str | None = None) -> str:
    """
    Plot time series lines for each keyword from a raw Google Trends CSV
    saved by the pipeline (expects columns: date, <keywords...>).
    """
    df = pd.read_csv(raw_csv_path, parse_dates=["date"]) if os.path.isfile(raw_csv_path) else pd.read_csv(raw_csv_path)
    if "date" not in df.columns:
        raise ValueError("Input CSV must contain a 'date' column.")

    _ensure_dir(os.path.join("reports", "figures"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_svg_path is None:
        output_svg_path = os.path.join("reports", "figures", f"trends_timeseries_{ts}.svg")

    plt.figure(figsize=(10, 6))
    for col in [c for c in df.columns if c != "date"]:
        plt.plot(df["date"], df[col], label=col)
    plt.xlabel("Date")
    plt.ylabel("Interest")
    plt.title("Google Trends Time Series")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(output_svg_path, format="svg")
    plt.close()
    return output_svg_path


def plot_topics_bar(topics_terms_csv: str, output_svg_path: str | None = None) -> str:
    """
    Plot top terms per cluster as a simple bar chart showing term counts per cluster
    (counts derived from comma-separated top_terms).
    Expects CSV with columns: cluster, top_terms
    """
    df = pd.read_csv(topics_terms_csv)
    if not {"cluster", "top_terms"}.issubset(set(df.columns)):
        raise ValueError("Input CSV must contain 'cluster' and 'top_terms' columns.")

    # Build counts
    rows = []
    for _, r in df.iterrows():
        cluster = r["cluster"]
        terms = [t.strip() for t in str(r["top_terms"]).split(",") if t.strip()]
        rows.append({"cluster": cluster, "term_count": len(terms)})
    plot_df = pd.DataFrame(rows)

    _ensure_dir(os.path.join("reports", "figures"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_svg_path is None:
        output_svg_path = os.path.join("reports", "figures", f"topics_bar_{ts}.svg")

    plt.figure(figsize=(8, 5))
    plt.bar(plot_df["cluster"].astype(str), plot_df["term_count"], color="#1f77b4")
    plt.xlabel("Cluster")
    plt.ylabel("Top Term Count")
    plt.title("Topic Model: Top Terms per Cluster")
    plt.tight_layout()
    plt.savefig(output_svg_path, format="svg")
    plt.close()
    return output_svg_path