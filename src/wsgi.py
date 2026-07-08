"""
ASGI entrypoint. Run with:

  uvicorn src.api.main:app --host 0.0.0.0 --port 5000

Or:

  uvicorn src.api.app:app --host 0.0.0.0 --port 5000
"""

from src.api.main import app

__all__ = ["app"]
