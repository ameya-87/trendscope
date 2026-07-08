import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

from src.config.settings import config
from src.scraping.google_trends_scraper import fetch_trends
from src.scraping.twitter_scraper import scrape_and_save as scrape_twitter
from src.scraping.reddit_scraper import scrape_and_save as scrape_reddit
from src.scraping.youtube_scraper import scrape_and_save as scrape_youtube
from src.scraping.tvmaze_scraper import scrape_and_save as scrape_tvmaze
from src.analysis.trend_detection import process_raw_trends
from src.dashboard.powerbi_export import export_for_powerbi


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _parse_keywords(keywords_str: str) -> list[str]:
    return [k.strip() for k in keywords_str.split(",") if k.strip()]


def run_google_trends(timeframe: str = "now 7-d", geo: str = "") -> str:
    """
    Ingest Google Trends for configured keywords and save raw CSV to data/raw.
    Returns the path to the saved raw CSV file.
    """
    keywords = _parse_keywords(config.KEYWORDS)
    trends_df = fetch_trends(keywords, timeframe=timeframe, geo=geo)

    _ensure_dir(os.path.join("data", "raw"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = os.path.join("data", "raw", f"google_trends_{ts}.csv")

    # Ensure index is a column named 'date' for downstream processing
    out_df = trends_df.reset_index()
    out_df.to_csv(raw_path, index=False)
    print(f"✅ Raw trends saved: {raw_path}")
    return raw_path


def visualize_momentum(processed_csv_path: str) -> str:
    """
    Simple visualization: bar chart of momentum per keyword, saved as SVG.
    """
    df = pd.read_csv(processed_csv_path)
    # Expected columns from trend_detection: keyword, latest_value, momentum, last_date, trend_direction
    df = df.sort_values("momentum", ascending=False)

    _ensure_dir(os.path.join("reports", "figures"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    svg_path = os.path.join("reports", "figures", f"trends_momentum_{ts}.svg")

    plt.figure(figsize=(10, 6))
    colors = df["trend_direction"].map({"up": "#2ca02c", "down": "#d62728", "flat": "#7f7f7f"}).fillna("#1f77b4")
    plt.bar(df["keyword"], df["momentum"], color=colors)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Momentum (latest - baseline)")
    plt.title("Google Trends Momentum by Keyword")
    plt.tight_layout()
    plt.savefig(svg_path, format="svg")
    plt.close()

    print(f"📈 SVG saved: {svg_path}")
    return svg_path


def main() -> None:
    # Phase 1: Minimal end-to-end with Google Trends
    raw_csv = run_google_trends()
    processed_csv = process_raw_trends(raw_csv)
    visualize_momentum(processed_csv)

    # Phase 2: Social media scraping and Power BI export
    print("\n--- Starting social media scraping ---")
    # scrape_twitter() # Temporarily disabled due to missing API key
    # scrape_reddit() # Temporarily disabled due to missing API key
    # scrape_youtube() # Temporarily disabled due to missing API key
    scrape_tvmaze()
    print("--- Social media scraping complete ---")

    print("\n--- Exporting data for Power BI ---")
    export_for_powerbi()
    print("--- Power BI export complete ---")


if __name__ == "__main__":
    main()