"""Wikimedia REST: daily top pageviews (no API key)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

from src.scraping.cache_ttl import cached

logger = logging.getLogger(__name__)
BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top"
DEFAULT_PROJECT = "en.wikipedia"
TIMEOUT = 25
HEADERS = {"User-Agent": "TrendScope/1.0 (dashboard; +https://github.com/)", "Accept": "application/json"}


def fetch_top_pageviews(
    project: str = DEFAULT_PROJECT,
    days_ago: int = 1,
    limit: int = 30,
) -> list[dict]:
    """
    Fetch top viewed articles for a given Wikimedia project.
    Tries UTC dates from `days_ago` up to 7 days back (Wikimedia may not publish the latest day yet).
    """
    limit = max(1, min(limit, 100))
    base_offset = max(1, days_ago)

    def _load_for_day(day) -> list[dict] | None:
        y, m, d = day.year, f"{day.month:02d}", f"{day.day:02d}"
        url = f"{BASE}/{project}/all-access/{y}/{m}/{d}"
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        payload = r.json()
        items = (payload or {}).get("items") or []
        articles = items[0].get("articles", []) if items else []
        out: list[dict] = []
        for row in articles[:limit]:
            art = row.get("article", "")
            out.append({
                "source": "wikipedia",
                "keyword": art.replace("_", " "),
                "views": int(row.get("views", 0) or 0),
                "rank": row.get("rank"),
            })
        return out

    def _load() -> list[dict]:
        today_utc = datetime.now(timezone.utc).date()
        for extra in range(8):
            day = today_utc - timedelta(days=base_offset + extra)
            try:
                chunk = _load_for_day(day)
                if chunk is not None:
                    return chunk
            except Exception:
                logger.debug("Wikipedia skip day %s", day, exc_info=True)
                continue
        return []

    today_utc = datetime.now(timezone.utc).date()
    first_day = today_utc - timedelta(days=base_offset)
    y0, m0, d0 = first_day.year, f"{first_day.month:02d}", f"{first_day.day:02d}"
    cache_key = f"wiki:{project}:{y0}{m0}{d0}:{limit}"

    try:
        return cached(cache_key, 600.0, _load, cache_empty=False)
    except Exception:
        logger.exception("Wikipedia pageviews fetch failed")
        return []
