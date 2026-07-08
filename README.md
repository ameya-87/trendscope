TrendScope

Overview
TrendScope collects, analyzes, and visualizes online trend signals. It ingests Google Trends, TVMaze, Wikipedia (pageviews), Hacker News, TMDB, CoinGecko, and YouTube (Data API), computes momentum for search trends, serves a web UI and REST API (FastAPI), and exports CSVs for Power BI.

Problem Statement
Trend signals are scattered across sources. TrendScope provides a single pipeline to ingest, normalize, score, and expose trends for analytics and dashboards.

Goals
- Unified pipeline for multiple data sources
- Clear momentum scoring and lightweight visualization
- Ready for Power BI and future ML forecasting

Features
- Ingestion: Google Trends, TVMaze, Wikipedia, Hacker News, TMDB, CoinGecko, YouTube (Twitter/Reddit stubs)
- Processing: momentum and trend direction (Google)
- API: FastAPI JSON endpoints (+ health + status)
- Frontend: Chart.js + Three.js dashboards
- Exports: Power BI-ready CSVs

Architecture
- Scraping: src/scraping/*_scraper.py and related modules
- Analysis: src/analysis (trend detection, topic modeling stubs)
- API: FastAPI in src/api/main.py; static UI from frontend/
- Visualization: reports/figures/*.svg
- Dashboard exports: reports/powerbi/*.csv

Tech Stack (rationale)
- Python + Pandas for ETL/analytics
- FastAPI + Uvicorn for API and static file hosting
- PyTrends, Requests for data sources
- Google API client for YouTube Data API v3
- Matplotlib/Chart.js for quick visuals

Installation
1) Python 3.11+
2) Create venv and install deps:
   - python -m venv venv
   - venv\Scripts\activate
   - pip install -r requirements.txt
3) Copy .env.example to .env and set values (see below)

Configuration (.env)
- KEYWORDS="AI, Bitcoin, Climate Change"
- ENABLE_YOUTUBE=1, ENABLE_WIKIPEDIA=1, ENABLE_HACKERNEWS=1, ENABLE_TMDB=1, ENABLE_COINGECKO=1
- YOUTUBE_API_KEY= (YouTube Data API v3)
- TMDB_API_KEY= (free key from themoviedb.org)
- TWITTER_BEARER_TOKEN=, REDDIT_* (optional; pipeline stubs)
Note: Env vars are read from the OS. In PowerShell, set with: $env:KEYWORDS="AI, Bitcoin".

Quick Start
- Run pipeline (optional, seeds data/raw):
  python src\run_pipeline.py
- Start API (dev):
  python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 5000
- Open UI:
  http://127.0.0.1:5000/

Deployment
- Production-style:
  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 5000 --workers 2

API Endpoints
- GET /api/health
- GET /api/status (which API keys / toggles are active)
- GET /api/google_presets
- GET /api/google_trends?preset=Tech&timeframe=now 7-d&geo=&lookback=4
- GET /api/trends_momentum (processed CSV, or computed from latest google_trends_*.csv)
- GET /api/social_posts (latest reddit_*.csv)
- GET /api/tv_trends (TVMaze; fetches live if no CSV in data/raw)
- GET /api/wiki_trends?limit=30
- GET /api/hn_trends?limit=30
- GET /api/movie_trends?kind=movie|tv&limit=20 (TMDB; needs TMDB_API_KEY)
- GET /api/crypto_trends?limit=15
- GET /api/youtube_trends?mode=trending|search&region=US&max_results=25&preset=Tech&days=7 (needs YOUTUBE_API_KEY)

Frontend usage
- Served at /. Use controls per panel; TMDB and YouTube need keys in .env for non-empty data.

Data attribution
- Wikipedia pageviews: Wikimedia REST API; data under CC BY-SA / applicable Wikimedia terms.
- TMDB: This product uses the TMDB API but is not endorsed or certified by TMDB.
- CoinGecko: follow https://www.coingecko.com/en/api/terms
- YouTube: YouTube Data API; subject to Google API terms of service.
- TVMaze: TVMaze API.

Power BI exports
- Generate CSVs:
  python -m src.dashboard.powerbi_export
- Outputs to reports/powerbi/

Troubleshooting
- No Google data: check internet and pytrends; try /api/google_trends; ensure keywords are valid.
- Empty Wikipedia: API may lag; the scraper retries older UTC dates automatically.
- TMDB/YouTube empty: set TMDB_API_KEY and YOUTUBE_API_KEY.
- TVMaze 429: retry later; reduce refresh frequency.
- Port in use: change the port in the uvicorn command.

Roadmap
- Platforms: deeper Twitter/Reddit/Instagram when keys and policies allow
- ML: topic modeling (BERTopic/spaCy/LDA), forecasting (Prophet/ARIMA/XGBoost/transformers), anomaly/early-signal detection.

References
- Figures: reports/figures/*.svg
- Data: data/raw and data/processed
- Notes: reports/roadmap.md

Contributing
- Fork and open PRs; ensure code compiles by running: python -m compileall -q src.

License
- MIT License. See LICENSE for details.

CI
- GitHub Actions runs a basic syntax validation on each push and PR.
