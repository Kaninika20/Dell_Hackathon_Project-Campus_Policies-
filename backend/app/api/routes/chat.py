from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ChatRequest, ChatResponse
from app.core.embeddings import get_query_embedding
from app.services.hybrid_retrieval import multi_mode_retrieve
from app.services.context_builder import build_evidence_context
from app.services.generator_service import generate_grounded_answer
from app.services.response_formatter import format_chat_response
from app.services.guardrails import sanitise_user_query
from app.services.semantic_cache import SemanticCacheManager

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    RAG query endpoint supporting multi-mode retrieval and state-aware semantic caching:
    - Checks exact query cache (O(1)) under current policy knowledge base fingerprint.
    - Checks semantic similarity cache using query embedding (cosine similarity >= threshold).
    - If hit, returns cached response instantly (< 50ms) avoiding redundant Gemini generation.
    - If miss, executes full grounded retrieval pipeline, synthesizes answer, and populates cache.
    - Automatically invalidates whenever policy documents are uploaded, modified, or deleted.
    """
    raw_question = request.question.strip()
    if not raw_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The question field cannot be empty or blank."
        )

    req_start = time.perf_counter()

    # ── 1. Sanitise user query for prompt injection ───────────────────────────
    sanitised_question, query_injection_detected = sanitise_user_query(raw_question)

    method = request.retrieval_method or "baseline"
    cache_mgr = SemanticCacheManager.get_instance()

    try:
        # ── 2. Exact Cache Lookup (O(1)) ──────────────────────────────────────
        exact_hit = cache_mgr.lookup_exact(sanitised_question, method)
        if exact_hit:
            lat = round((time.perf_counter() - req_start) * 1000, 2)
            meta = {
                "retrieval_method": method,
                "cached": True,
                "cache_type": "exact",
                "state_fingerprint": exact_hit.get("state_fingerprint"),
                "latency_ms": lat,
                "chunks_retrieved": len(exact_hit.get("sources", [])),
                "query_injection_detected": query_injection_detected,
                "chunk_injection_detected": False,
                "policy_conflicts": [],
                "version_warning_issued": False,
            }
            return format_chat_response(
                answer=exact_hit["answer"],
                evidence_list=exact_hit.get("sources", []),
                retrieval_method=method,
                confidence=None,
                retrieval_metadata=meta
            )

        # ── 3. Query Embedding & Semantic Cache Lookup ────────────────────────
        query_vec = get_query_embedding(sanitised_question)
        semantic_hit = cache_mgr.lookup_semantic(query_vec, method)
        if semantic_hit:
            lat = round((time.perf_counter() - req_start) * 1000, 2)
            meta = {
                "retrieval_method": method,
                "cached": True,
                "cache_type": "semantic",
                "similarity_score": semantic_hit.get("similarity_score"),
                "state_fingerprint": semantic_hit.get("state_fingerprint"),
                "latency_ms": lat,
                "chunks_retrieved": len(semantic_hit.get("sources", [])),
                "query_injection_detected": query_injection_detected,
                "chunk_injection_detected": False,
                "policy_conflicts": [],
                "version_warning_issued": False,
            }
            return format_chat_response(
                answer=semantic_hit["answer"],
                evidence_list=semantic_hit.get("sources", []),
                retrieval_method=method,
                confidence=None,
                retrieval_metadata=meta
            )

        # ── 4. Cache Miss: Execute Full Retrieval Pipeline ────────────────────
        cache_mgr.record_miss()
        chunks, retrieval_meta = multi_mode_retrieve(
            query=sanitised_question,
            method=method,
            top_k=request.top_k
        )

        # ── 5. Build sanitised context + guardrail metadata ───────────────────
        context_str, evidence_list, guardrail_meta = build_evidence_context(chunks)

        # ── 6. Grounded synthesis using sanitised query ───────────────────────
        raw_answer = generate_grounded_answer(sanitised_question, context_str)

        # ── 7. Prepend version warning to answer (if any) ─────────────────────
        version_warning = guardrail_meta.get("version_warning", "")
        final_answer = f"{version_warning}\n\n{raw_answer}".strip() if version_warning else raw_answer

        # ── 8. Store in Semantic Cache ────────────────────────────────────────
        cache_mgr.set(
            query=sanitised_question,
            query_vector=query_vec,
            retrieval_method=method,
            response_data={
                "answer": final_answer,
                "sources": evidence_list,
            }
        )

        # ── 9. Merge retrieval + guardrail metadata ───────────────────────────
        total_lat = round((time.perf_counter() - req_start) * 1000, 2)
        combined_meta = {
            **retrieval_meta,
            "cached": False,
            "cache_type": None,
            "state_fingerprint": cache_mgr.get_state_fingerprint(),
            "query_injection_detected": query_injection_detected,
            "chunk_injection_detected": guardrail_meta["chunk_injection_detected"],
            "policy_conflicts": guardrail_meta["policy_conflicts"],
            "version_warning_issued": bool(version_warning),
            "latency_ms": total_lat,
        }

        # ── 10. Format and return ─────────────────────────────────────────────
        return format_chat_response(
            answer=final_answer,
            evidence_list=evidence_list,
            retrieval_method=retrieval_meta["retrieval_method"],
            confidence=None,
            retrieval_metadata=combined_meta
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation error: {str(e)}"
        )
