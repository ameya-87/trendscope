"""The Movie Database (TMDB) v3 trending and search (free API key)."""

from __future__ import annotations

import logging
from typing import Literal

import requests

from src.config.settings import config
from src.scraping.cache_ttl import cached

logger = logging.getLogger(__name__)
BASE = "https://api.themoviedb.org/3"
TIMEOUT = 25
HEADERS = {"User-Agent": "TrendScope/1.0 (dashboard)"}

MediaKind = Literal["movie", "tv"]


def _row_from_result(row: dict, kind: MediaKind) -> dict:
    title = row.get("title") or row.get("name") or ""
    return {
        "source": "tmdb",
        "media_kind": kind,
        "keyword": title,
        "rating": float(row["vote_average"]) if row.get("vote_average") is not None else None,
        "votes": int(row.get("vote_count", 0) or 0),
        "overview": (row.get("overview") or "")[:280],
        "url": f"https://www.themoviedb.org/{kind}/{row.get('id')}",
    }


def fetch_trending(kind: MediaKind = "movie", limit: int = 20) -> list[dict]:
    key = config.TMDB_API_KEY
    if not key:
        return []

    limit = max(1, min(limit, 40))
    cache_key = f"tmdb:trending:{kind}:{limit}"

    def _load() -> list[dict]:
        url = f"{BASE}/trending/{kind}/day"
        r = requests.get(url, params={"api_key": key}, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        results = r.json().get("results") or []
        return [_row_from_result(row, kind) for row in results[:limit]]

    try:
        return cached(cache_key, 600.0, _load, cache_empty=False)
    except Exception:
        logger.exception("TMDB trending failed")
        return []


def search_media(kind: MediaKind, query: str, limit: int = 15) -> list[dict]:
    key = config.TMDB_API_KEY
    q = (query or "").strip()
    if not key or not q:
        return []
    limit = max(1, min(limit, 20))
    path = "movie" if kind == "movie" else "tv"
    cache_key = f"tmdb:search:{path}:{q.lower()}:{limit}"

    def _load() -> list[dict]:
        url = f"{BASE}/search/{path}"
        r = requests.get(
            url,
            params={"api_key": key, "query": q, "page": 1},
            timeout=TIMEOUT,
            headers=HEADERS,
        )
        r.raise_for_status()
        results = r.json().get("results") or []
        return [_row_from_result(row, kind) for row in results[:limit]]

    try:
        return cached(cache_key, 600.0, _load, cache_empty=False)
    except Exception:
        logger.exception("TMDB search failed")
        return []


def fetch_for_interests(
    kind: MediaKind,
    topics: list[str],
    trending_limit: int = 10,
    search_per_query: int = 5,
) -> list[dict]:
    """Trending plus search results for the first few topic strings."""
    seen: set[str] = set()
    out: list[dict] = []
    for row in fetch_trending(kind=kind, limit=trending_limit):
        k = row.get("keyword") or ""
        if k in seen:
            continue
        seen.add(k)
        out.append(row)
    for topic in topics[:5]:
        t = (topic or "").strip()
        if len(t) < 2:
            continue
        for row in search_media(kind, t, limit=search_per_query):
            k = row.get("keyword") or ""
            if k in seen:
                continue
            seen.add(k)
            out.append(row)
    return out[:30]
