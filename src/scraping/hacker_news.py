"""Hacker News public Firebase API (no key)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from src.scraping.cache_ttl import cached

logger = logging.getLogger(__name__)
TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
TIMEOUT = 15
HEADERS = {"User-Agent": "TrendScope/1.0 (dashboard)"}


def _fetch_item(session: requests.Session, item_id: int) -> dict[str, Any] | None:
    try:
        r = session.get(ITEM_URL.format(id=item_id), timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def fetch_top_stories(limit: int = 30) -> list[dict]:
    limit = max(1, min(limit, 50))
    cache_key = f"hn:top:{limit}"

    def _load() -> list[dict]:
        r = requests.get(TOP_URL, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        ids = r.json()
        if not isinstance(ids, list):
            return []
        ids = ids[:limit]
        out: list[dict] = []
        with requests.Session() as session:
            for iid in ids:
                data = _fetch_item(session, int(iid))
                if not data or data.get("type") != "story" or not data.get("title"):
                    continue
                out.append({
                    "source": "hacker_news",
                    "keyword": data.get("title", "")[:200],
                    "score": int(data.get("score", 0) or 0),
                    "url": data.get("url") or f"https://news.ycombinator.com/item?id={iid}",
                    "comments": int(data.get("descendants", 0) or 0),
                })
        return out

    try:
        return cached(cache_key, 120.0, _load, cache_empty=False)
    except Exception:
        logger.exception("Hacker News fetch failed")
        return []
