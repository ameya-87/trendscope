import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    _ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


def get_env(name: str, default: str | None = None, *, strip: bool = False) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    if strip:
        value = value.strip()
        return value if value else None
    return value


@dataclass
class Config:
    # API Keys / Tokens (strip avoids .env quoting/whitespace breaking API auth)
    YOUTUBE_API_KEY: str | None = get_env("YOUTUBE_API_KEY", strip=True)
    TMDB_API_KEY: str | None = get_env("TMDB_API_KEY", strip=True)
    TWITTER_BEARER_TOKEN: str | None = get_env("TWITTER_BEARER_TOKEN")
    REDDIT_CLIENT_ID: str | None = get_env("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: str | None = get_env("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: str | None = get_env("REDDIT_USER_AGENT", "TrendScope/1.0 by user")

    # Pipeline toggles
    ENABLE_YOUTUBE: bool = get_env("ENABLE_YOUTUBE", "1") == "1"
    ENABLE_TWITTER: bool = get_env("ENABLE_TWITTER", "0") == "1"
    ENABLE_REDDIT: bool = get_env("ENABLE_REDDIT", "0") == "1"
    ENABLE_WIKIPEDIA: bool = get_env("ENABLE_WIKIPEDIA", "1") == "1"
    ENABLE_HACKERNEWS: bool = get_env("ENABLE_HACKERNEWS", "1") == "1"
    ENABLE_TMDB: bool = get_env("ENABLE_TMDB", "1") == "1"
    ENABLE_COINGECKO: bool = get_env("ENABLE_COINGECKO", "1") == "1"

    # Keywords (comma-separated string)
    KEYWORDS: str = get_env("KEYWORDS", "AI, Bitcoin, Climate Change")
    KEYWORD_PRESETS: dict[str, list[str]] = field(default_factory=lambda: {
        "Tech": ["AI", "Machine Learning", "Blockchain", "Quantum Computing", "Cybersecurity", "Cloud Computing", "IoT"],
        "Sports": ["Premier League", "NBA", "NFL", "Cristiano Ronaldo", "Lionel Messi", "Olympics", "F1"],
        "Finance": ["Bitcoin", "Stock Market", "Inflation", "Gold", "Interest Rates", "Nasdaq", "Ethereum"],
        "Entertainment": ["Taylor Swift", "Marvel", "Netflix", "Game of Thrones", "Anime", "K-pop", "Disney"]
    })


config = Config()