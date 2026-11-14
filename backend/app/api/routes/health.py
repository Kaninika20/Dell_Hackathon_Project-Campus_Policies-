from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.core.qdrant_client import get_qdrant_client
from app.models.schemas import HealthResponse
from app.services.semantic_cache import SemanticCacheManager

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Service health check."""
    qdrant_ok = False
    try:
        client = get_qdrant_client()
        client.get_collections()
        qdrant_ok = True
    except Exception:
        pass

    gemini_configured = bool(settings.gemini_api_key)
    cache_mgr = SemanticCacheManager.get_instance()

    return HealthResponse(
        status="ok",
        qdrant_ok=qdrant_ok,
        gemini_configured=gemini_configured,
        redis_available=cache_mgr.is_redis_available,
        cache_enabled=settings.enable_semantic_cache,
    )

