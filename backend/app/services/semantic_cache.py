"""
semantic_cache.py — State-Aware Semantic & Exact Caching Layer

Features:
1. Redis-backed caching with automatic, thread-safe in-memory fallback.
2. Exact query match (normalized string hash).
3. Semantic query match using Cosine Similarity on Gemini embeddings.
4. Document version & knowledge-base state fingerprint embedded in cache keys.
5. Invalidation ensures outdated policy answers are NEVER served.
"""
from __future__ import annotations

import json
import math
import hashlib
import threading
import time
from typing import List, Dict, Any, Optional, Tuple

import redis
from app.core.config import settings
from app.services.document_registry import DocumentRegistry


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class SemanticCacheManager:
    """
    Manages semantic and exact caching for policy queries.
    Uses Redis when available, falls back transparently to in-memory store.
    """
    _instance: Optional[SemanticCacheManager] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._redis_client: Optional[redis.Redis] = None
        self._redis_available: bool = False
        self._in_memory_cache: Dict[str, Dict[str, Any]] = {}
        self._in_memory_vectors: List[Dict[str, Any]] = []  # list of {key, vector, state, method}
        # Telemetry metrics
        self._total_lookups: int = 0
        self._exact_hits: int = 0
        self._semantic_hits: int = 0
        self._misses: int = 0
        self._estimated_ms_saved: float = 0.0
        self._init_connection()

    def _init_connection(self) -> None:
        """Attempts to connect to Redis."""
        try:
            r = redis.Redis.from_url(
                settings.redis_url,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                decode_responses=True
            )
            r.ping()
            self._redis_client = r
            self._redis_available = True
        except Exception:
            self._redis_client = None
            self._redis_available = False

    @classmethod
    def get_instance(cls) -> SemanticCacheManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def is_redis_available(self) -> bool:
        return self._redis_available

    def _normalize_query(self, query: str) -> str:
        """Normalizes query for exact hash matching."""
        return " ".join(query.strip().lower().split())

    def _get_exact_key(self, query: str, method: str, state_fingerprint: str) -> str:
        norm = self._normalize_query(query)
        q_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
        return f"cp:cache:{state_fingerprint}:{method}:{q_hash}"

    def get_state_fingerprint(self) -> str:
        return DocumentRegistry.get_instance().get_state_fingerprint()

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Returns cumulative cache metrics and estimated latency savings."""
        with self._lock:
            total_hits = self._exact_hits + self._semantic_hits
            lookups = self._total_lookups if self._total_lookups > 0 else (total_hits + self._misses)
            hit_rate = round((total_hits / lookups) * 100, 1) if lookups > 0 else 0.0
            return {
                "redis_available": self._redis_available,
                "cache_enabled": settings.enable_semantic_cache,
                "current_state_fingerprint": self.get_state_fingerprint(),
                "total_lookups": lookups,
                "total_hits": total_hits,
                "exact_hits": self._exact_hits,
                "semantic_hits": self._semantic_hits,
                "misses": self._misses,
                "hit_rate_pct": hit_rate,
                "in_memory_cached_entries": len(self._in_memory_cache),
                "in_memory_vector_entries": len(self._in_memory_vectors),
                "estimated_latency_saved_ms": round(self._estimated_ms_saved, 2),
            }

    def record_miss(self) -> None:
        with self._lock:
            self._total_lookups += 1
            self._misses += 1

    def lookup_exact(
        self,
        query: str,
        retrieval_method: str
    ) -> Optional[Dict[str, Any]]:
        """
        O(1) exact query lookup under the current knowledge-base state.
        """
        if not settings.enable_semantic_cache:
            return None

        state = self.get_state_fingerprint()
        key = self._get_exact_key(query, retrieval_method, state)

        # 1. Try Redis
        if self._redis_available and self._redis_client:
            try:
                data = self._redis_client.get(key)
                if data:
                    res = json.loads(data)
                    res["cache_hit"] = True
                    res["cache_type"] = "exact"
                    with self._lock:
                        self._total_lookups += 1
                        self._exact_hits += 1
                        self._estimated_ms_saved += 2500.0
                    return res
            except Exception:
                self._redis_available = False

        # 2. Try In-memory fallback
        with self._lock:
            cached = self._in_memory_cache.get(key)
            if cached:
                res = dict(cached)
                res["cache_hit"] = True
                res["cache_type"] = "exact"
                self._total_lookups += 1
                self._exact_hits += 1
                self._estimated_ms_saved += 2500.0
                return res

        return None

    def lookup_semantic(
        self,
        query_vector: List[float],
        retrieval_method: str,
        threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Cosine similarity search over cached query vectors under the current state.
        If similarity >= threshold, returns the cached answer without calling LLM.
        """
        if not settings.enable_semantic_cache or not query_vector:
            return None

        sim_threshold = threshold if threshold is not None else settings.semantic_cache_threshold
        state = self.get_state_fingerprint()

        best_score = -1.0
        best_entry_key: Optional[str] = None

        # 1. Search in-memory vector index (mirrored from Redis / memory)
        with self._lock:
            # Filter vectors matching CURRENT state fingerprint & retrieval method
            candidate_vectors = [
                v for v in self._in_memory_vectors
                if v.get("state") == state and v.get("method") == retrieval_method
            ]

            for cand in candidate_vectors:
                sim = cosine_similarity(query_vector, cand["vector"])
                if sim > best_score:
                    best_score = sim
                    best_entry_key = cand["key"]

        if best_entry_key and best_score >= sim_threshold:
            # Fetch response data
            result_data = None
            if self._redis_available and self._redis_client:
                try:
                    data_str = self._redis_client.get(best_entry_key)
                    if data_str:
                        result_data = json.loads(data_str)
                except Exception:
                    self._redis_available = False

            if not result_data:
                with self._lock:
                    cached = self._in_memory_cache.get(best_entry_key)
                    if cached:
                        result_data = dict(cached)

            if result_data:
                with self._lock:
                    self._total_lookups += 1
                    self._semantic_hits += 1
                    self._estimated_ms_saved += 2500.0
                result_data["cache_hit"] = True
                result_data["cache_type"] = "semantic"
                result_data["similarity_score"] = round(best_score, 4)
                return result_data

        return None

    # ── Storage ───────────────────────────────────────────────────────────────

    def set(
        self,
        query: str,
        query_vector: List[float],
        retrieval_method: str,
        response_data: Dict[str, Any]
    ) -> None:
        """
        Stores response in cache linked to the current document state fingerprint.
        """
        if not settings.enable_semantic_cache:
            return

        state = self.get_state_fingerprint()
        key = self._get_exact_key(query, retrieval_method, state)

        # Store payload
        payload = {
            "query": query,
            "answer": response_data.get("answer"),
            "sources": response_data.get("sources", []),
            "retrieval_method": retrieval_method,
            "state_fingerprint": state,
            "timestamp": time.time(),
        }

        # 1. Write to Redis
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.setex(
                    key,
                    settings.cache_ttl_seconds,
                    json.dumps(payload)
                )
            except Exception:
                self._redis_available = False

        # 2. Write to In-Memory Cache
        with self._lock:
            self._in_memory_cache[key] = payload
            if query_vector:
                # Retain in vector index
                self._in_memory_vectors.append({
                    "key": key,
                    "vector": query_vector,
                    "state": state,
                    "method": retrieval_method,
                    "query": query,
                })
                # Cap in-memory vector index to 500 items (FIFO)
                if len(self._in_memory_vectors) > 500:
                    self._in_memory_vectors.pop(0)

    # ── Invalidation ──────────────────────────────────────────────────────────

    def invalidate_all(self) -> int:
        """
        Invalidates all cached entries across all states.
        Called on explicit reset or global cache purge.
        """
        count = 0
        with self._lock:
            count += len(self._in_memory_cache)
            self._in_memory_cache.clear()
            self._in_memory_vectors.clear()

        if self._redis_available and self._redis_client:
            try:
                keys = self._redis_client.keys("cp:cache:*")
                if keys:
                    count += len(keys)
                    self._redis_client.delete(*keys)
            except Exception:
                pass

        return count

    def purge_stale_entries(self) -> int:
        """
        Purges cached entries belonging to outdated state fingerprints.
        """
        current_state = self.get_state_fingerprint()
        purged = 0

        with self._lock:
            # Purge memory
            stale_keys = [k for k, v in self._in_memory_cache.items() if v.get("state_fingerprint") != current_state]
            for k in stale_keys:
                self._in_memory_cache.pop(k, None)
                purged += 1
            self._in_memory_vectors = [v for v in self._in_memory_vectors if v.get("state") == current_state]

        # Purge Redis
        if self._redis_available and self._redis_client:
            try:
                all_keys = self._redis_client.keys("cp:cache:*")
                for k in all_keys:
                    if f":{current_state}:" not in k:
                        self._redis_client.delete(k)
                        purged += 1
            except Exception:
                pass

        return purged

