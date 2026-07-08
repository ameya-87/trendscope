# src/scraping/twitter_scraper.py

import os
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


def fetch_twitter_posts(keyword_list: List[str], max_results_per_kw: int = 50, lang: str = "en") -> pd.DataFrame:
    """
    Fetch recent Tweets per keyword using Twitter API v2 (Recent Search).

    Requires TWITTER_BEARER_TOKEN in environment.

    Unified schema columns:
      source, published_at, keyword, title, text, url, author, views, likes, comments
    """
    bearer = config.TWITTER_BEARER_TOKEN
    if not bearer:
        raise RuntimeError("Missing TWITTER_BEARER_TOKEN in environment.")

    headers = {"Authorization": f"Bearer {bearer}"}

    rows: List[Dict] = []

    for kw in keyword_list:
        # Basic query: exclude retweets to reduce duplication
        query = f"{kw} lang:{lang} -is:retweet"
        params = {
            "query": query,
            "max_results": max(10, min(max_results_per_kw, 100)),
            "tweet.fields": "created_at,public_metrics,lang",
            "expansions": "author_id",
            "user.fields": "username,name"
        }
        resp = requests.get("https://api.twitter.com/2/tweets/search/recent", headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            # Rate-limited; return what we have so far for this keyword
            print(f"⚠️ Rate limited for keyword '{kw}'. Consider reducing max_results or increasing interval.")
            continue
        resp.raise_for_status()
        data = resp.json()

        tweets = data.get("data", [])
        users = data.get("includes", {}).get("users", [])
        user_map = {u.get("id"): (u.get("username") or u.get("name") or "") for u in users}

        for t in tweets:
            tid = t.get("id")
            text = t.get("text")
            created_at = t.get("created_at")
            author_id = t.get("author_id")
            public_metrics = t.get("public_metrics", {})
            like_count = public_metrics.get("like_count")
            reply_count = public_metrics.get("reply_count")
            # view_count is not generally available in standard API

            author = user_map.get(author_id, None)
            url = f"https://twitter.com/i/web/status/{tid}" if tid else None

            # Title: a short preview (first 80 chars) of the tweet text
            preview = (text or "")[:80]

            rows.append({
                "source": "twitter",
                "published_at": created_at,
                "keyword": kw,
                "title": preview,
                "text": text,
                "url": url,
                "author": author,
                "views": None,
                "likes": like_count,
                "comments": reply_count,
            })

    df = pd.DataFrame(rows)
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[UNIFIED_COLUMNS]


def save_to_csv(df: pd.DataFrame) -> str:
    _ensure_dir(os.path.join('data', 'raw'))
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join('data', 'raw', f'twitter_{ts}.csv')
    df.to_csv(out_path, index=False)
    return out_path


def scrape_and_save(keywords: List[str] | None = None, max_results_per_kw: int = 50, lang: str = "en") -> str:
    if keywords is None or len(keywords) == 0:
        keywords = _parse_keywords(config.KEYWORDS)
    try:
        df = fetch_twitter_posts(keywords, max_results_per_kw=max_results_per_kw, lang=lang)
        df = clean_dataframe(df, text_column="text", output_column="cleaned_text")
    except Exception as e:
        # Return an empty CSV with correct schema to keep pipeline moving
        df = pd.DataFrame(columns=UNIFIED_COLUMNS)
        print(f"⚠️ Twitter scrape error: {e}. Writing empty dataset.")
    path = save_to_csv(df)
    return path


if __name__ == '__main__':
    out = scrape_and_save()
    print(f"✅ Twitter data saved to {out}")