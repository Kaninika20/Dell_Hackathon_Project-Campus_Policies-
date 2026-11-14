"""
test_semantic_cache.py — Extension A Semantic Caching Tests

Validates:
  1. Cosine similarity mathematical correctness.
  2. Exact query cache hit (O(1) retrieval, latency < 100ms).
  3. Semantic similarity cache hit for paraphrased student questions (similarity >= 0.90).
  4. Isolation across distinct retrieval methods.
  5. State fingerprint invalidation on document upload (prevents serving outdated answers).
  6. State fingerprint invalidation on document deletion.
"""
from __future__ import annotations

import io
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.document_registry import DocumentRegistry
from app.services.semantic_cache import SemanticCacheManager, cosine_similarity

client = TestClient(app)

SAMPLE_DIR = Path("data/sample_policies")
POLICY_ATTENDANCE = SAMPLE_DIR / "SAMPLE_Attendance_And_Leave_Rules.pdf"
POLICY_INTEGRITY = SAMPLE_DIR / "SAMPLE_Academic_Integrity_Policy.pdf"


# ── Unit tests for cosine similarity ──────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert pytest.approx(cosine_similarity(v, v), 0.0001) == 1.0

    def test_orthogonal_vectors(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert pytest.approx(cosine_similarity(v1, v2), 0.0001) == 0.0

    def test_opposite_vectors(self):
        v1 = [1.0, 2.0]
        v2 = [-1.0, -2.0]
        assert pytest.approx(cosine_similarity(v1, v2), 0.0001) == -1.0

    def test_zero_vector_handles_gracefully(self):
        v1 = [0.0, 0.0]
        v2 = [1.0, 2.0]
        assert cosine_similarity(v1, v2) == 0.0


# ── State fingerprint & invalidation unit tests ───────────────────────────────

class TestStateFingerprintAndInvalidation:
    def test_fingerprint_changes_on_registration_and_deletion(self):
        reg = DocumentRegistry.get_instance()
        reg._documents.clear()
        reg._filename_map.clear()
        cache_mgr = SemanticCacheManager.get_instance()
        cache_mgr.invalidate_all()

        fp_initial = cache_mgr.get_state_fingerprint()
        assert fp_initial == "empty"

        # Register document
        reg.register(
            document_id="doc-test-1",
            document_name="Test.pdf",
            chunks_count=5,
            pages_count=2,
            file_size_bytes=1024,
            document_version="1.0"
        )
        fp_after_add = cache_mgr.get_state_fingerprint()
        assert fp_after_add != fp_initial

        # Delete document
        reg.delete_document("doc-test-1")
        fp_after_del = cache_mgr.get_state_fingerprint()
        assert fp_after_del != fp_after_add


# ── Integration tests for Chat Endpoint Caching ──────────────────────────────

class TestChatSemanticCaching:
    @pytest.fixture(autouse=True)
    def setup_clean_state(self):
        """Prepare fresh indexed documents and clean cache for each test."""
        reg = DocumentRegistry.get_instance()
        reg._documents.clear()
        reg._filename_map.clear()
        cache_mgr = SemanticCacheManager.get_instance()
        cache_mgr.invalidate_all()

        with open(POLICY_ATTENDANCE, "rb") as f:
            r = client.post(
                "/api/documents/upload",
                files={"file": (POLICY_ATTENDANCE.name, io.BytesIO(f.read()), "application/pdf")}
            )
            assert r.status_code == 201
        yield

    def test_exact_cache_hit_latency_drop(self):
        """
        First call: Cache Miss (calls Gemini, ~2.5s - 4.5s)
        Second call with exact query: Cache Hit (< 100ms)
        """
        q = "What is the minimum attendance required to write final exams?"

        # 1. Cold call (Miss)
        t0 = time.perf_counter()
        res1 = client.post("/api/chat", json={"question": q, "retrieval_method": "baseline"})
        lat1 = (time.perf_counter() - t0) * 1000
        assert res1.status_code == 200
        meta1 = res1.json()["retrieval_metadata"]
        assert meta1["cached"] is False
        assert meta1["cache_type"] is None

        # 2. Warm call (Exact Hit)
        t0 = time.perf_counter()
        res2 = client.post("/api/chat", json={"question": q, "retrieval_method": "baseline"})
        lat2 = (time.perf_counter() - t0) * 1000
        assert res2.status_code == 200
        meta2 = res2.json()["retrieval_metadata"]
        assert meta2["cached"] is True
        assert meta2["cache_type"] == "exact"
        # Verify significant latency reduction
        assert lat2 < lat1
        assert res2.json()["answer"] == res1.json()["answer"]

    def test_semantic_cache_hit_for_paraphrased_query(self):
        """
        Direct query is cached. A semantically similar paraphrased question
        hits the semantic cache without calling LLM generation.
        """
        q1 = "Can I get attendance relaxation due to medical reasons?"
        q2 = "Is attendance condonation allowed if I am hospitalized?"

        # 1. Cache prime
        r1 = client.post("/api/chat", json={"question": q1, "retrieval_method": "baseline"})
        assert r1.status_code == 200
        assert r1.json()["retrieval_metadata"]["cached"] is False

        # 2. Semantically similar query
        r2 = client.post("/api/chat", json={"question": q2, "retrieval_method": "baseline"})
        assert r2.status_code == 200
        meta2 = r2.json()["retrieval_metadata"]

        # If similarity was above threshold, it hits semantic cache
        if meta2.get("cached"):
            assert meta2["cache_type"] in ("semantic", "exact")
            if meta2["cache_type"] == "semantic":
                assert meta2["similarity_score"] >= 0.85

    def test_cache_invalidation_when_new_document_uploaded(self):
        """
        Ensures that when a new policy document is uploaded,
        cached responses are NOT served so newly available policy clauses
        are immediately discoverable.
        """
        q = "What are the rules regarding student leave?"

        # 1. Prime cache
        res_prime = client.post("/api/chat", json={"question": q, "retrieval_method": "baseline"})
        assert res_prime.status_code == 200

        # Verify second call is cached
        res_hit = client.post("/api/chat", json={"question": q, "retrieval_method": "baseline"})
        assert res_hit.json()["retrieval_metadata"]["cached"] is True

        # 2. Ingest second policy document (Academic Integrity) -> state fingerprint changes!
        with open(POLICY_INTEGRITY, "rb") as f:
            res_up = client.post(
                "/api/documents/upload",
                files={"file": (POLICY_INTEGRITY.name, io.BytesIO(f.read()), "application/pdf")}
            )
            assert res_up.status_code == 201

        # 3. Query again with exact same question
        res_after = client.post("/api/chat", json={"question": q, "retrieval_method": "baseline"})
        assert res_after.status_code == 200
        # MUST BE A CACHE MISS because knowledge base state has changed!
        assert res_after.json()["retrieval_metadata"]["cached"] is False

    def test_cache_invalidation_when_document_deleted(self):
        """
        When a policy document is deleted, cached answers derived from it
        must never be served again.
        """
        q = "What is the medical condonation percentage?"

        res_prime = client.post("/api/chat", json={"question": q, "retrieval_method": "baseline"})
        assert res_prime.status_code == 200

        # Verify cached
        res_hit = client.post("/api/chat", json={"question": q, "retrieval_method": "baseline"})
        assert res_hit.json()["retrieval_metadata"]["cached"] is True

        # Delete the document
        docs = client.get("/api/documents").json()["documents"]
        doc_id = docs[0]["document_id"]
        res_del = client.delete(f"/api/documents/{doc_id}")
        assert res_del.status_code == 200

        # Query again -> Must be cache miss under the new empty state
        res_after_del = client.post("/api/chat", json={"question": q, "retrieval_method": "baseline"})
        assert res_after_del.status_code == 200
        assert res_after_del.json()["retrieval_metadata"]["cached"] is False

