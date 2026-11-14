from __future__ import annotations

"""Hybrid retrieval service: BM25 + Qdrant vector search with Reciprocal Rank Fusion."""

from typing import List, Dict, Any

import google.generativeai as genai

from app.core.config import settings
from app.core.embeddings import get_query_embedding
from app.core.qdrant_client import get_qdrant_client
from app.models.schemas import SourceChunk, QueryResponse
from app.services.bm25_store import BM25Store


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def _reciprocal_rank_fusion(
    bm25_results: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Fuse two ranked lists using RRF.  Returns deduplicated results sorted by fused score."""
    scores: Dict[str, float] = {}
    chunks_by_id: Dict[str, Dict[str, Any]] = {}

    def _id(chunk: Dict[str, Any]) -> str:
        return chunk.get("id", chunk["text"][:80])

    for rank, chunk in enumerate(bm25_results, start=1):
        cid = _id(chunk)
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunks_by_id[cid] = chunk

    for rank, chunk in enumerate(vector_results, start=1):
        cid = _id(chunk)
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunks_by_id[cid] = chunk

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    result = []
    for cid in ranked_ids:
        chunk = dict(chunks_by_id[cid])
        chunk["rrf_score"] = scores[cid]
        result.append(chunk)
    return result


# ---------------------------------------------------------------------------
# Vector search
# ---------------------------------------------------------------------------

def _vector_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    query_vec = get_query_embedding(query)
    client = get_qdrant_client()
    hits = client.search(
        collection_name=settings.qdrant_collection_name,
        query_vector=query_vec,
        limit=top_k,
        with_payload=True,
    )
    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append(
            {
                "id": str(hit.id),
                "text": payload.get("text", ""),
                "page": payload.get("page", 0),
                "document": payload.get("document", "unknown"),
                "vector_score": hit.score,
            }
        )
    return results


# ---------------------------------------------------------------------------
# LLM answer synthesis
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are CampusPolicy AI, an assistant that answers questions about university policies.
Answer ONLY based on the provided policy excerpts.
If the answer is not found in the excerpts, say so clearly.
Always cite the document and page number for each key point.
Be concise and factual. Do not fabricate information.
"""


def _synthesize_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return (
            "I could not find relevant information in the uploaded policy documents. "
            "Please ensure the relevant policy PDF has been uploaded."
        )

    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"[Excerpt {i} — {chunk['document']}, Page {chunk['page']}]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Policy Excerpts:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer:"
    )

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_generative_model)
    response = model.generate_content(prompt)
    return response.text.strip()


# ---------------------------------------------------------------------------
# Main retrieval entry point
# ---------------------------------------------------------------------------

def hybrid_retrieve_and_answer(question: str, top_k: int | None = None) -> QueryResponse:
    k = top_k or settings.top_k

    bm25_store = BM25Store.get_instance()
    bm25_results = bm25_store.search(question, top_k=k)
    vector_results = _vector_search(question, top_k=k)

    fused = _reciprocal_rank_fusion(bm25_results, vector_results)
    top_chunks = fused[:k]

    answer = _synthesize_answer(question, top_chunks)

    sources = [
        SourceChunk(
            document=c["document"],
            page=c["page"],
            text=c["text"][:300] + ("..." if len(c["text"]) > 300 else ""),
            score=round(c.get("rrf_score", 0.0), 4),
        )
        for c in top_chunks
    ]

    return QueryResponse(answer=answer, sources=sources, question=question)

