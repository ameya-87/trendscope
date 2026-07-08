"""CoinGecko public API: trending search and coin search (no key; respect rate limits)."""

from __future__ import annotations

import logging
from typing import Iterable

import requests

from src.scraping.cache_ttl import cached

logger = logging.getLogger(__name__)
TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"
SEARCH_URL = "https://api.coingecko.com/api/v3/search"
TIMEOUT = 25
HEADERS = {"User-Agent": "TrendScope/1.0 (dashboard)"}


def _coin_row_from_search_item(c: dict, order_score: int) -> dict:
    cid = c.get("id") or ""
    return {
        "source": "coingecko",
        "keyword": c.get("name") or c.get("symbol") or cid,
        "symbol": (c.get("symbol") or "").upper(),
        "rank": c.get("market_cap_rank"),
        "score": max(1, order_score),
        "url": f"https://www.coingecko.com/en/coins/{cid}" if cid else "",
    }


def fetch_trending_coins(limit: int = 15) -> list[dict]:
    limit = max(1, min(limit, 20))
    cache_key = f"coingecko:trending:{limit}"

    def _load() -> list[dict]:
        r = requests.get(TRENDING_URL, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        coins = r.json().get("coins") or []
        out: list[dict] = []
        for i, entry in enumerate(coins[:limit]):
            item = entry.get("item") or {}
            out.append({
                "source": "coingecko",
                "keyword": item.get("name") or item.get("symbol") or "",
                "symbol": (item.get("symbol") or "").upper(),
                "rank": item.get("market_cap_rank"),
                "score": max(1, limit - i),
                "url": f"https://www.coingecko.com/en/coins/{item.get('id')}" if item.get("id") else "",
            })
        return out

    try:
        return cached(cache_key, 300.0, _load, cache_empty=False)
    except Exception:
        logger.exception("CoinGecko trending failed")
        return []


def search_coins(query: str, limit: int = 8) -> list[dict]:
    q = (query or "").strip()
    if not q:
        return []
    cache_key = f"coingecko:search:{q.lower()}:{limit}"

    def _load() -> list[dict]:
        r = requests.get(SEARCH_URL, params={"query": q}, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        raw = r.json().get("coins") or []
        out: list[dict] = []
        for i, c in enumerate(raw[:limit]):
            out.append(_coin_row_from_search_item(c, 40 - i * 2))
        return out

    try:
        return cached(cache_key, 300.0, _load, cache_empty=False)
    except Exception:
        logger.exception("CoinGecko search failed for %s", query)
        return []


def fetch_coins_for_interests(topics: Iterable[str], trending_limit: int = 12, per_topic: int = 4) -> list[dict]:
    """Trending list plus search hits for each topic (deduped by url)."""
    seen: set[str] = set()
    merged: list[dict] = []
    for row in fetch_trending_coins(limit=trending_limit):
        u = row.get("url") or row.get("keyword")
        if u in seen:
            continue
        seen.add(u)
        merged.append(row)
    for topic in topics:
        t = (topic or "").strip()
        if not t:
            continue
        for row in search_coins(t, limit=per_topic):
            u = row.get("url") or row.get("keyword")
            if u in seen:
                continue
            seen.add(u)
            merged.append(row)
    return merged[: max(trending_limit, 20)]
