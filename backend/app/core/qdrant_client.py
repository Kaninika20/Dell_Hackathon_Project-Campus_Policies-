from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient

from app.core.config import settings


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Return a cached Qdrant client.

    Uses QDRANT_URL and optionally QDRANT_API_KEY from settings.
    If QDRANT_URL is empty or ':memory:', returns an in-memory client.
    """
    url = settings.qdrant_url.strip()
    api_key = settings.qdrant_api_key.strip() or None

    if not url or url == ":memory:":
        return QdrantClient(":memory:")

    return QdrantClient(url=url, api_key=api_key)

