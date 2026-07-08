# src/scraping/reddit_scraper.py

import os
import time
from datetime import datetime
from typing import List, Dict
import requests
import pandas as pd

from config.settings import config
from processing.text_cleaning import clean_dataframe


UNIFIED_COLUMNS = [
    "source", "published_at", "keyword", "title", "text", "url", "author", "views", "likes", "comments"
]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _parse_keywords(keywords_str: str) -> List[str]:
    return [k.strip() for k in keywords_str.split(',') if k.strip()]


def _iso8601_from_utc(ts_utc: float) -> str:
    return datetime.utcfromtimestamp(ts_utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _get_reddit_token() -> str:
    """Obtain an application-only OAuth token for Reddit API."""
    client_id = config.REDDIT_CLIENT_ID
    client_secret = config.REDDIT_CLIENT_SECRET
    user_agent = config.REDDIT_USER_AGENT or "TrendScope/1.0"

    if not client_id or not client_secret:
        raise RuntimeError("Missing Reddit credentials: REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET.")

    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": user_agent}
    resp = requests.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers, timeout=20)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Failed to obtain Reddit access token.")
    return token


def fetch_reddit_posts(keyword_list: List[str], max_results_per_kw: int = 25) -> pd.DataFrame:
    """
    Fetch recent Reddit posts per keyword using the Reddit API.

    Unified schema columns:
      source, published_at, keyword, title, text, url, author, views, likes, comments
    """
    user_agent = config.REDDIT_USER_AGENT or "TrendScope/1.0"
    token = _get_reddit_token()
    headers = {"Authorization": f"Bearer {token}", "User-Agent": user_agent}

    rows: List[Dict] = []

    for kw in keyword_list:
        params = {
            "q": kw,
            "sort": "new",
            "limit": min(max_results_per_kw, 100),
            "restrict_sr": False,
            "include_over_18": "on",
            "type": "link"
        }
        # Use a simple search endpoint
        resp = requests.get("https://oauth.reddit.com/search", headers=headers, params=params, timeout=30)
        if resp.status_code == 401:
            # Token may have expired; retry once
            token = _get_reddit_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = requests.get("https://oauth.reddit.com/search", headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            title = d.get("title")
            selftext = d.get("selftext")
            url = d.get("url")
            author = d.get("author")
            created_utc = d.get("created_utc")
            score = d.get("score")  # upvotes
            num_comments = d.get("num_comments")

            rows.append({
                "source": "reddit",
                "published_at": _iso8601_from_utc(created_utc) if isinstance(created_utc, (int, float)) else None,
                "keyword": kw,
                "title": title,
                "text": selftext,
                "url": url,
                "author": author,
                "views": None,  # not available via this endpoint
                "likes": score,
                "comments": num_comments,
            })

        # Be polite with API
        time.sleep(0.5)

    df = pd.DataFrame(rows)
    # Ensure unified schema columns exist
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[UNIFIED_COLUMNS]


def save_to_csv(df: pd.DataFrame) -> str:
    _ensure_dir(os.path.join('data', 'raw'))
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join('data', 'raw', f'reddit_{ts}.csv')
    df.to_csv(out_path, index=False)
    return out_path


def scrape_and_save(keywords: List[str] | None = None, max_results_per_kw: int = 25) -> str:
    if keywords is None or len(keywords) == 0:
        keywords = _parse_keywords(config.KEYWORDS)
    try:
        df = fetch_reddit_posts(keywords, max_results_per_kw=max_results_per_kw)
        df = clean_dataframe(df, text_column="text", output_column="cleaned_text")
    except Exception as e:
        # Return an empty CSV with correct schema to keep pipeline moving
        df = pd.DataFrame(columns=UNIFIED_COLUMNS)
        print(f"⚠️ Reddit scrape error: {e}. Writing empty dataset.")
    path = save_to_csv(df)
    return path


if __name__ == '__main__':
    out = scrape_and_save()
    print(f"✅ Reddit data saved to {out}")