from __future__ import annotations

import time
from typing import List, Dict, Any, Tuple

from app.core.config import settings
from app.core.embeddings import get_query_embedding
from app.core.qdrant_client import get_qdrant_client
from app.services.bm25_store import BM25Store
from app.services.hyde_service import generate_hypothetical_document


def _search_qdrant_by_vector(vector: List[float], top_k: int) -> List[Dict[str, Any]]:
    client = get_qdrant_client()
    collections = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection_name not in collections:
        return []

    hits = client.search(
        collection_name=settings.qdrant_collection_name,
        query_vector=vector,
        limit=top_k,
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


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Applies Reciprocal Rank Fusion (RRF) across multiple ranked lists.
    RRF Score = Sum_i ( 1 / (k + rank_i) )
    """
    rrf_scores: Dict[str, float] = {}
    chunk_map: Dict[str, Dict[str, Any]] = {}

    for r_list in ranked_lists:
        for rank, item in enumerate(r_list, start=1):
            cid = item.get("chunk_id") or item.get("text")[:80]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))
            if cid not in chunk_map:
                chunk_map[cid] = item

    sorted_cids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    fused_results: List[Dict[str, Any]] = []
    for cid in sorted_cids:
        c = dict(chunk_map[cid])
        c["rrf_score"] = rrf_scores[cid]
        fused_results.append(c)

    return fused_results


def multi_mode_retrieve(
    query: str,
    method: str = "baseline",
    top_k: int | None = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Executes retrieval according to the chosen mode:
    1. 'baseline': Direct question vector search on Qdrant
    2. 'hyde': Generates hypothetical administrative excerpt -> Vector search on Qdrant
    3. 'hyde_hybrid': HyDE vector search + BM25 keyword search -> Reciprocal Rank Fusion

    Returns:
      (retrieved_chunks, metadata_dict)
    """
    k = top_k or settings.top_k
    start_time = time.perf_counter()
    method_normalized = method.lower().strip()
    meta: Dict[str, Any] = {
        "retrieval_method": method_normalized,
        "top_k": k,
        "hypothetical_passage": None
    }

    if method_normalized == "baseline":
        # Direct query vector search
        query_vec = get_query_embedding(query)
        chunks = _search_qdrant_by_vector(query_vec, k)

    elif method_normalized == "hyde":
        # 1. HyDE generation
        hypo_doc = generate_hypothetical_document(query)
        meta["hypothetical_passage"] = hypo_doc
        # 2. Vector search using hypothetical document embedding
        hypo_vec = get_query_embedding(hypo_doc)
        chunks = _search_qdrant_by_vector(hypo_vec, k)

    elif method_normalized in ["hyde_hybrid", "hybrid"]:
        method_normalized = "hyde_hybrid"
        meta["retrieval_method"] = "hyde_hybrid"
        
        # 1. HyDE branch
        hypo_doc = generate_hypothetical_document(query)
        meta["hypothetical_passage"] = hypo_doc
        hypo_vec = get_query_embedding(hypo_doc)
        dense_results = _search_qdrant_by_vector(hypo_vec, k * 2)

        # 2. BM25 keyword branch (queries on original query keywords)
        bm25_store = BM25Store.get_instance()
        sparse_results = bm25_store.search(query, top_k=k * 2)

        # 3. Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion([dense_results, sparse_results], k=60)
        chunks = fused[:k]
    else:
        raise ValueError(f"Unknown retrieval method: '{method}'. Choose 'baseline', 'hyde', or 'hyde_hybrid'.")

    meta["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
    meta["chunks_retrieved"] = len(chunks)
    return chunks, meta

