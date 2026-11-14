from __future__ import annotations

from typing import List, Dict, Any

from app.core.config import settings
from app.core.embeddings import get_query_embedding
from app.core.qdrant_client import get_qdrant_client


def retrieve_baseline_chunks(query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
    """
    Baseline dense vector retrieval:
    1. Embed query with Gemini embedding model.
    2. Search Qdrant collection for top_k closest points.
    3. Return payload metadata and vector similarity score.
    """
    k = top_k or settings.top_k
    query_vector = get_query_embedding(query)
    client = get_qdrant_client()
    
    # Check if collection exists
    collections = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection_name not in collections:
        return []

    hits = client.search(
        collection_name=settings.qdrant_collection_name,
        query_vector=query_vector,
        limit=k,
        with_payload=True
    )

    results: List[Dict[str, Any]] = []
    for hit in hits:
        payload = hit.payload or {}
        results.append({
            "chunk_id": payload.get("chunk_id", str(hit.id)),
            "document_id": payload.get("document_id", ""),
            "document_name": payload.get("document_name", "Unknown Document"),
            "page_number": payload.get("page_number", 1),
            "section_heading": payload.get("section_heading", "General Policy"),
            "text": payload.get("text", ""),
            "score": float(hit.score),
            "upload_timestamp": payload.get("upload_timestamp", ""),
            "document_version": payload.get("document_version", "1.0"),
        })

    return results

