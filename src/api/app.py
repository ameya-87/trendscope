"""ASGI application re-export for `uvicorn src.api.app:app`."""

from src.api.main import app

__all__ = ["app"]
