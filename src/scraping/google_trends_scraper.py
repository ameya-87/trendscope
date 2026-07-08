# src/scraping/google_trends_scraper.py

from pytrends.request import TrendReq
import pandas as pd
import os
from datetime import datetime

# Initialize pytrends
pytrends = TrendReq(hl='en-US', tz=330)

def fetch_trends(keyword_list, timeframe="now 7-d", geo=""):
    """
    Fetch Google Trends data for a list of keywords.
    
    Args:
        keyword_list (list): List of keywords to track
        timeframe (str): Time range (default: past 7 days)
        geo (str): Country code (default: worldwide)
        
    Returns:
        DataFrame: Trend data
    """
    if not keyword_list:
        return pd.DataFrame()
    max_terms = 5
    frames = []
    for i in range(0, len(keyword_list), max_terms):
        chunk = keyword_list[i:i+max_terms]
        pytrends.build_payload(chunk, cat=0, timeframe=timeframe, geo=geo, gprop='')
        data = pytrends.interest_over_time()
        if "isPartial" in data.columns:
            data = data.drop(columns=["isPartial"])
        frames.append(data)
    if not frames:
        return pd.DataFrame()
    merged = frames[0]
    for df in frames[1:]:
        merged = merged.join(df, how="outer")
    return merged

if __name__ == "__main__":
    keywords = ["AI", "Bitcoin", "Climate Change"]  # You can edit this list
    trends = fetch_trends(keywords)

    # Save results to data/raw
    os.makedirs("data/raw", exist_ok=True)
    filename = f"data/raw/google_trends_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    trends.to_csv(filename)

    print(f"✅ Trends data saved to {filename}")
