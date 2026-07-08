"""
TrendScope FastAPI application: REST API + static frontend.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Literal

import pandas as pd
from googleapiclient.errors import HttpError
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.analysis.trend_detection import compute_keyword_momentum, wide_to_long
from src.config.settings import config
from src.scraping.coingecko_scraper import fetch_coins_for_interests, fetch_trending_coins
from src.scraping.google_trends_scraper import fetch_trends
from src.scraping.hacker_news import fetch_top_stories
from src.scraping.tmdb_scraper import fetch_for_interests as fetch_tmdb_for_interests
from src.scraping.tmdb_scraper import fetch_trending as fetch_tmdb_trending
from src.scraping.tvmaze_scraper import scrape_top_shows
from src.scraping.wikipedia_pageviews import fetch_top_pageviews
from src.scraping.youtube_scraper import fetch_youtube_trending, fetch_youtube_videos
from src.pipeline.snapshot_runner import GoogleSnapshotRequest, run_google_snapshot
from src.storage.snapshots_db import get_default_db
from src.ml.google_spike_model import (
    predict_google_spike_probability,
    load_models,
)






FRONTEND_DIR = os.path.abspath(os.path.join(ROOT_DIR, "frontend"))
DATA_DIR = os.path.abspath(os.path.join(ROOT_DIR, "data"))
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="TrendScope API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_topics_param(topics: str | None) -> list[str]:
    if not topics or not topics.strip():
        return []
    return [t.strip() for t in topics.split(",") if t.strip()]


def _filter_rows_by_topics(rows: list[dict], topics: str | None) -> list[dict]:
    tl = _parse_topics_param(topics)
    if not tl or not rows:
        return rows
    filt = [r for r in rows if any(t.lower() in (r.get("keyword") or "").lower() for t in tl)]
    return filt if filt else rows


def get_latest_csv(directory: str, prefix: str) -> str | None:
    try:
        if not os.path.isdir(directory):
            return None
        files = [f for f in os.listdir(directory) if f.startswith(prefix) and f.endswith(".csv")]
        if not files:
            return None
        latest = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
        return os.path.join(directory, latest)
    except Exception:
        logger.exception("Error scanning directory %s for prefix %s", directory, prefix)
        return None


def _tv_show_records(df: pd.DataFrame) -> list[dict]:
    df = df.copy()
    df["rating_average"] = df.get("rating_average", df.get("rating", None))
    records: list[dict] = []
    for _, row in df.iterrows():
        genres = row.get("genres", "")
        if isinstance(genres, str):
            genres_str = genres
        elif isinstance(genres, list):
            genres_str = ", ".join(genres)
        else:
            genres_str = ""
        records.append({
            "keyword": str(row.get("name", "")),
            "rating": float(row["rating_average"]) if pd.notnull(row.get("rating_average")) else None,
            "genres": genres_str,
            "status": str(row.get("status", "")),
            "language": str(row.get("language", "")),
            "network": str(row.get("network_name", "")),
            "web_channel": str(row.get("webChannel_name", "")),
            "premiered": str(row.get("premiered", "")),
            "official_site": str(row.get("officialSite", "")),
            "schedule_time": str(row.get("schedule_time", "")),
            "schedule_days": str(row.get("schedule_days", "")),
            "updated": str(row.get("updated", "")),
            "summary": str(row.get("summary", "")),
        })
    records.sort(
        key=lambda x: (x["rating"] if x["rating"] is not None else -1, x["keyword"]),
        reverse=True,
    )
    return records[:50]


def _tv_episode_aggregate(df: pd.DataFrame) -> list[dict]:
    if "keyword" not in df.columns:
        return []
    if "published_at" in df.columns:
        try:
            df = df.copy()
            df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
        except Exception:
            pass
    grouped = df.groupby("keyword", dropna=True)
    trends: list[dict] = []
    for keyword, group in grouped:
        count = int(len(group))
        latest_idx = group["published_at"].idxmax() if "published_at" in group.columns else group.index[0]
        latest_row = df.loc[latest_idx] if latest_idx in df.index else group.iloc[0]
        trends.append({
            "keyword": str(keyword),
            "count": count,
            "latest_title": str(latest_row["title"]) if "title" in df.columns else "",
            "latest_url": str(latest_row["url"]) if "url" in df.columns else "",
            "latest_published_at": latest_row["published_at"].isoformat()
            if "published_at" in df.columns and pd.notnull(latest_row.get("published_at"))
            else "",
        })
    trends.sort(key=lambda x: x["count"], reverse=True)
    return trends


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@app.get("/api/status")
def api_status():
    return {
        "youtube_configured": bool(config.YOUTUBE_API_KEY) and config.ENABLE_YOUTUBE,
        "tmdb_configured": bool(config.TMDB_API_KEY),
        "twitter_configured": bool(config.TWITTER_BEARER_TOKEN),
        "wikipedia_enabled": config.ENABLE_WIKIPEDIA,
        "hackernews_enabled": config.ENABLE_HACKERNEWS,
        "tmdb_enabled": config.ENABLE_TMDB,
        "coingecko_enabled": config.ENABLE_COINGECKO,
    }


@app.get("/api/wiki_trends")
def wiki_trends(
    limit: int = Query(30, ge=1, le=100),
    topics: str | None = Query(None, description="Comma-separated; filter top articles (substring match)"),
):
    if not config.ENABLE_WIKIPEDIA:
        return []
    fetch_n = max(limit * 2, 80)
    rows = fetch_top_pageviews(limit=min(fetch_n, 200))
    tl = _parse_topics_param(topics)
    if tl:
        filt = [
            r
            for r in rows
            if any(t.lower() in (r.get("keyword") or "").lower() for t in tl)
        ]
        rows = filt if filt else rows
    return rows[:limit]


@app.get("/api/hn_trends")
def hn_trends(
    limit: int = Query(30, ge=1, le=50),
    topics: str | None = Query(None, description="Comma-separated; filter story titles"),
):
    if not config.ENABLE_HACKERNEWS:
        return []
    rows = fetch_top_stories(limit=max(limit, 50))
    tl = _parse_topics_param(topics)
    if tl:
        filt = [
            r
            for r in rows
            if any(t.lower() in (r.get("keyword") or "").lower() for t in tl)
        ]
        rows = filt if filt else rows
    return rows[:limit]


@app.get("/api/movie_trends")
def movie_trends(
    kind: Literal["movie", "tv"] = Query("movie"),
    limit: int = Query(20, ge=1, le=40),
    topics: str | None = Query(None, description="Comma-separated; search + trending merge"),
):
    if not config.ENABLE_TMDB or not config.TMDB_API_KEY:
        return []
    tl = _parse_topics_param(topics)
    if tl:
        rows = fetch_tmdb_for_interests(kind, tl, trending_limit=min(limit, 12))
        return rows[:limit]
    return fetch_tmdb_trending(kind=kind, limit=limit)


@app.get("/api/crypto_trends")
def crypto_trends(
    limit: int = Query(15, ge=1, le=25),
    topics: str | None = Query(None, description="Comma-separated; trending + coin search per topic"),
):
    if not config.ENABLE_COINGECKO:
        return []
    tl = _parse_topics_param(topics)
    if tl:
        rows = fetch_coins_for_interests(tl, trending_limit=limit, per_topic=4)
        return rows[:limit]
    return fetch_trending_coins(limit=limit)


def _youtube_error_payload(message: str) -> dict[str, Any]:
    return {"items": [], "error": message}


def _youtube_ok_payload(rows: list[dict]) -> dict[str, Any]:
    return {"items": rows, "error": None}


@app.get("/api/youtube_trends")
def youtube_trends(
    mode: Literal["trending", "search"] = Query("trending"),
    region: str = Query("US"),
    max_results: int = Query(25, ge=1, le=50),
    preset: str | None = None,
    days: int = Query(7, ge=1, le=30),
    keywords: str | None = Query(
        None,
        description="Comma-separated search terms (overrides preset when mode=search)",
    ),
):
    if not config.YOUTUBE_API_KEY or not config.ENABLE_YOUTUBE:
        return _youtube_error_payload(
            "YouTube is disabled or YOUTUBE_API_KEY is not set. Add the key to .env in the project root and restart the server."
        )
    try:
        if mode == "trending":
            rows = fetch_youtube_trending(region_code=region, max_results=max_results)
            return _youtube_ok_payload(rows)
        kw_override = _parse_topics_param(keywords)
        if kw_override:
            keywords_list = kw_override
        elif preset and preset in config.KEYWORD_PRESETS:
            keywords_list = config.KEYWORD_PRESETS[preset]
        else:
            keywords_list = [k.strip() for k in config.KEYWORDS.split(",") if k.strip()]
        if not keywords_list:
            return _youtube_error_payload(
                "No search keywords: set topics above, pick a preset, or set KEYWORDS in .env."
            )
        df = fetch_youtube_videos(
            keywords_list,
            days=days,
            max_results_per_kw=min(max_results, 50),
        )
        if df.empty:
            return _youtube_ok_payload([])
        return _youtube_ok_payload(df.to_dict(orient="records"))
    except HttpError as e:
        msg = f"YouTube API HTTP {e.resp.status}"
        try:
            if e.content:
                body = json.loads(e.content.decode())
                inner = (body.get("error") or {}).get("message")
                if inner:
                    msg = inner
        except Exception:
            msg = f"{msg}: {e!s}"
        logger.exception("YouTube trends failed: %s", msg)
        hint = msg
        if e.resp.status in (403, 401):
            hint += (
                " If this key is restricted to websites (HTTP referrers), it will not work for server-side calls. "
                "Use an unrestricted key or IP restriction for your server."
            )
        return _youtube_error_payload(hint)
    except Exception as e:
        logger.exception("YouTube trends failed")
        return _youtube_error_payload(str(e) or "Unknown YouTube error")


@app.get("/api/trends_momentum")
def trends_momentum(lookback: int = Query(4, ge=2, le=30)):
    latest = get_latest_csv(PROCESSED_DIR, "trends_momentum_")
    if latest:
        try:
            df = pd.read_csv(latest)
            return df.to_dict(orient="records")
        except Exception:
            logger.exception("Failed to read trends momentum CSV: %s", latest)

    raw_path = get_latest_csv(RAW_DIR, "google_trends_")
    if raw_path:
        try:
            raw_df = pd.read_csv(raw_path)
            long_df = wide_to_long(raw_df)
            summary_df = compute_keyword_momentum(long_df, lookback=lookback)
            return summary_df.to_dict(orient="records")
        except Exception:
            logger.exception("Failed to process raw Google trends: %s", raw_path)

    return []


@app.get("/api/social_posts")
def social_posts():
    latest = get_latest_csv(RAW_DIR, "reddit_")
    if not latest:
        raise HTTPException(status_code=404, detail="No social posts data found")
    try:
        df = pd.read_csv(latest)
        return df.to_dict(orient="records")
    except Exception:
        logger.exception("Failed to read social posts CSV: %s", latest)
        raise HTTPException(status_code=500, detail="Failed to read social posts data") from None


@app.get("/api/tv_trends")
def tv_trends(topics: str | None = Query(None, description="Comma-separated; filter show titles")):
    raw_dir = RAW_DIR
    latest_tv_csv = get_latest_csv(raw_dir, "tvmaze_")
    if not latest_tv_csv:
        try:
            new_path = scrape_top_shows(pages=3)
            if new_path and os.path.isfile(new_path):
                latest_tv_csv = new_path
        except Exception:
            logger.exception("TVMaze live fetch failed")

    if not latest_tv_csv:
        raise HTTPException(status_code=404, detail="No TV trends data found")

    try:
        df = pd.read_csv(latest_tv_csv)
    except Exception:
        logger.exception("Failed to read TV trends CSV: %s", latest_tv_csv)
        raise HTTPException(status_code=500, detail="Failed to read TV trends data") from None

    if "name" in df.columns and ("rating_average" in df.columns or "rating" in df.columns):
        return _filter_rows_by_topics(_tv_show_records(df), topics)

    if "keyword" not in df.columns:
        raise HTTPException(status_code=500, detail="TV data missing keyword column")

    trends = _tv_episode_aggregate(df)
    if len(trends) <= 1:
        try:
            new_path = scrape_top_shows(pages=3)
            if new_path:
                df2 = pd.read_csv(new_path)
                if "name" in df2.columns:
                    return _filter_rows_by_topics(_tv_show_records(df2), topics)
        except Exception:
            pass
    return _filter_rows_by_topics(trends, topics)


@app.get("/api/google_presets")
def google_presets():
    return {"presets": list(config.KEYWORD_PRESETS.keys())}


@app.post("/api/snapshots/run_google")
@app.post("/api/snapshots/run_google/")
def run_google_snapshot_endpoint(
    timeframe: str = Query("now 7-d"),

    geo: str = Query(""),
    lookback: int = Query(4, ge=2, le=30),
    keywords: str | None = Query(None, description="Comma-separated; overrides KEYWORDS"),
):
    tl = _parse_topics_param(keywords)
    req = GoogleSnapshotRequest(
        timeframe=timeframe,
        geo=geo,
        lookback=lookback,
        keywords=tl if tl else None,
    )
    db = get_default_db()
    snapshot_id = run_google_snapshot(req, db=db)
    return {"snapshot_id": snapshot_id}


@app.get("/api/training/google_momentum")
def training_google_momentum(



    keyword: str | None = Query(None, description="If set, returns history only for this keyword"),
    from_snapshot_id: int | None = Query(None, ge=1),
    to_snapshot_id: int | None = Query(None, ge=1),
    limit: int = Query(200, ge=1, le=2000),
):
    db = get_default_db()
    rows = db.list_google_training_rows(
        keyword=keyword,
        from_snapshot_id=from_snapshot_id,
        to_snapshot_id=to_snapshot_id,
        limit=limit,
    )
    return rows


@app.get("/api/predictions/google_spike")
def predictions_google_spike(
    keyword: str = Query(..., description="Keyword to predict spike probability for"),
    delta: float = Query(1.0, ge=0.1, le=100.0, description="Spike threshold delta (must match model training)"),
):
    # Load latest trained model for this delta.
    # MVP: pick the newest file in reports/predictions matching delta.
    pred_dir = os.path.join(ROOT_DIR, "reports", "predictions")
    if not os.path.isdir(pred_dir):
        return {"keyword": keyword, "spike_probability": None, "error": "No prediction models directory found"}

    candidates = [
        os.path.join(pred_dir, f)
        for f in os.listdir(pred_dir)
        if f.startswith("google_spike_models_delta") and f.endswith(".joblib") and f"delta{delta}" in f
    ]
    if not candidates:
        # fallback: allow any delta model file
        candidates = [
            os.path.join(pred_dir, f)
            for f in os.listdir(pred_dir)
            if f.startswith("google_spike_models_delta") and f.endswith(".joblib")
        ]

    if not candidates:
        return {"keyword": keyword, "spike_probability": None, "error": "No trained spike model files found"}

    latest_model_path = max(candidates, key=lambda p: os.path.getmtime(p))
    try:
        trained_payload = load_models(latest_model_path)
        model_obj = trained_payload.get(keyword)
        if model_obj is None:
            return {"keyword": keyword, "spike_probability": None, "error": f"No model trained for keyword '{keyword}'"}
    except Exception as e:
        return {"keyword": keyword, "spike_probability": None, "error": f"Failed to load model: {e!s}"}

    db = get_default_db()
    # Use last N rows for the keyword; model feature uses most recent row only.
    latest_rows = db.list_keyword_momentum_for_keyword(keyword=keyword, limit=5)
    try:
        proba = predict_google_spike_probability(
            trained=model_obj,
            latest_rows=latest_rows,
        )
        return {"keyword": keyword, "spike_probability": proba, "delta": delta, "model_path": latest_model_path}
    except Exception as e:
        return {"keyword": keyword, "spike_probability": None, "delta": delta, "error": f"Prediction failed: {e!s}"}


@app.get("/api/google_trends")

def google_trends(
    preset: str | None = None,
    timeframe: str = "now 7-d",
    geo: str = "",
    lookback: int = 4,
    keywords: str | None = Query(
        None,
        description="Comma-separated topics (overrides preset when non-empty)",
    ),
):
    kw_custom = _parse_topics_param(keywords)
    if kw_custom:
        keywords_list = kw_custom
    elif preset and preset in config.KEYWORD_PRESETS:
        keywords_list = config.KEYWORD_PRESETS[preset]
    else:
        keywords_list = [k.strip() for k in config.KEYWORDS.split(",") if k.strip()]

    out_df = None
    try:
        df = fetch_trends(keywords_list, timeframe=timeframe, geo=geo)
        if df is not None and not df.empty:
            out_df = df.reset_index()
    except Exception:
        logger.exception("Failed to fetch Google trends")

    if out_df is None:
        latest_processed = get_latest_csv(PROCESSED_DIR, "trends_momentum_")
        if latest_processed:
            try:
                proc_df = pd.read_csv(latest_processed)
                return proc_df.to_dict(orient="records")
            except Exception:
                logger.exception("Failed to read processed momentum CSV: %s", latest_processed)
        latest_raw = get_latest_csv(RAW_DIR, "google_trends_")
        if latest_raw:
            try:
                raw_df = pd.read_csv(latest_raw)
                long_df_fb = wide_to_long(raw_df)
                summary_df_fb = compute_keyword_momentum(long_df_fb, lookback=lookback)
                return summary_df_fb.to_dict(orient="records")
            except Exception:
                logger.exception("Failed to process raw Google trends CSV: %s", latest_raw)
        return []

    try:
        os.makedirs(RAW_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = os.path.join(RAW_DIR, f"google_trends_{ts}.csv")
        out_df.to_csv(raw_path, index=False)
    except Exception:
        pass

    long_df = wide_to_long(out_df)
    summary_df = compute_keyword_momentum(long_df, lookback=lookback)
    return summary_df.to_dict(orient="records")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/style.css")
def serve_style():
    return FileResponse(os.path.join(FRONTEND_DIR, "style.css"))


@app.get("/script.js")
def serve_script():
    return FileResponse(os.path.join(FRONTEND_DIR, "script.js"))


@app.get("/three_animation.js")
def serve_three_animation():
    return FileResponse(os.path.join(FRONTEND_DIR, "three_animation.js"))
