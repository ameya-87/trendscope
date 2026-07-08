# src/scraping/youtube_scraper.py

import os
from datetime import datetime, timedelta
from typing import Any, List, Dict
import pandas as pd

from googleapiclient.discovery import build

from src.config.settings import config
from src.processing.text_cleaning import clean_dataframe


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _parse_keywords(keywords_str: str) -> List[str]:
    return [k.strip() for k in keywords_str.split(',') if k.strip()]


def _iso8601(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def _to_int(val: Any) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _youtube_client():
    api_key = config.YOUTUBE_API_KEY
    if not api_key:
        raise RuntimeError("Missing YOUTUBE_API_KEY in environment.")
    return build('youtube', 'v3', developerKey=api_key)


def fetch_youtube_trending(region_code: str = "US", max_results: int = 25) -> list[dict]:
    """
    Regional most popular videos (YouTube Data API v3 chart=mostPopular).
    """
    max_results = max(1, min(max_results, 50))
    youtube = _youtube_client()
    resp = youtube.videos().list(
        part='snippet,statistics',
        chart='mostPopular',
        regionCode=region_code or "US",
        maxResults=max_results,
    ).execute()

    rows: list[dict] = []
    for item in resp.get('items', []):
        vid = item.get('id')
        snip = item.get('snippet', {})
        stats = item.get('statistics', {})
        rows.append({
            'source': 'youtube',
            'keyword': snip.get('title') or '',
            'title': snip.get('title'),
            'published_at': snip.get('publishedAt'),
            'author': snip.get('channelTitle'),
            'views': _to_int(stats.get('viewCount')),
            'likes': _to_int(stats.get('likeCount')),
            'comments': _to_int(stats.get('commentCount')),
            'url': f'https://www.youtube.com/watch?v={vid}' if vid else None,
        })
    return rows


def fetch_youtube_videos(keyword_list: List[str], days: int = 7, max_results_per_kw: int = 25) -> pd.DataFrame:
    """
    Fetch recent YouTube videos for each keyword using the YouTube Data API v3.
    Requires YOUTUBE_API_KEY in environment.

    Unified schema columns:
      source, published_at, keyword, title, text, url, author, views, likes, comments
    """
    youtube = _youtube_client()
    published_after = _iso8601(datetime.utcnow() - timedelta(days=days))

    rows: List[Dict] = []

    for kw in keyword_list:
        search_req = youtube.search().list(
            part='snippet',
            q=kw,
            type='video',
            order='date',
            maxResults=min(max_results_per_kw, 50),
            publishedAfter=published_after,
            safeSearch='none'
        )
        search_resp = search_req.execute()
        video_ids = [item['id']['videoId'] for item in search_resp.get('items', []) if 'id' in item and 'videoId' in item['id']]
        if not video_ids:
            continue

        stats_req = youtube.videos().list(
            part='statistics,snippet',
            id=','.join(video_ids)
        )
        stats_resp = stats_req.execute()

        for item in stats_resp.get('items', []):
            vid = item.get('id')
            snip = item.get('snippet', {})
            stats = item.get('statistics', {})
            title = snip.get('title')
            description = snip.get('description')
            channel_title = snip.get('channelTitle')
            published_at = snip.get('publishedAt')

            url = f"https://www.youtube.com/watch?v={vid}" if vid else None

            rows.append({
                'source': 'youtube',
                'published_at': published_at,
                'keyword': kw,
                'title': title,
                'text': description,
                'url': url,
                'author': channel_title,
                'views': _to_int(stats.get('viewCount')),
                'likes': _to_int(stats.get('likeCount')),
                'comments': _to_int(stats.get('commentCount')),
            })

    return pd.DataFrame(rows)


def save_to_csv(df: pd.DataFrame) -> str:
    _ensure_dir(os.path.join('data', 'raw'))
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join('data', 'raw', f'youtube_{ts}.csv')
    df.to_csv(out_path, index=False)
    return out_path


def scrape_and_save(keywords: List[str] | None = None, days: int = 7, max_results_per_kw: int = 25) -> str:
    if keywords is None or len(keywords) == 0:
        keywords = _parse_keywords(config.KEYWORDS)
    df = fetch_youtube_videos(keywords, days=days, max_results_per_kw=max_results_per_kw)
    df = clean_dataframe(df, text_column="text", output_column="cleaned_text")
    path = save_to_csv(df)
    return path


if __name__ == '__main__':
    try:
        out = scrape_and_save()
        print(f"✅ YouTube data saved to {out}")
    except Exception as e:
        print(f"❌ Error scraping YouTube: {e}")
