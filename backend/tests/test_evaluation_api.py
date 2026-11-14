"""
test_evaluation_api.py — Evaluation Dashboard & Telemetry Endpoint Tests

Validates:
  1. GET /api/evaluation/benchmark returns actual empirical metrics across all 3 modes.
  2. Baseline, HyDE, and HyDE+Hybrid metrics conform to schema (Recall@5, Precision@5, MRR, Latency).
  3. GET /api/evaluation/cache-stats returns live hit/miss metrics and state fingerprint.
  4. POST /api/evaluation/cache-clear successfully purges cache.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.semantic_cache import SemanticCacheManager

client = TestClient(app)


class TestEvaluationEndpoints:
    def test_get_benchmark_metrics_structure(self):
        res = client.get("/api/evaluation/benchmark")
        assert res.status_code == 200
        data = res.json()

        assert "benchmark_metrics" in data
        assert "dataset_size" in data
        assert data["dataset_size"] == 16
        assert "sample_queries" in data
        assert len(data["sample_queries"]) == 16

        metrics = data["benchmark_metrics"]
        assert len(metrics) == 3
        modes = [m["mode"] for m in metrics]
        assert "baseline" in modes
        assert "hyde" in modes
        assert "hyde_hybrid" in modes

        for m in metrics:
            assert 0.0 <= m["recall_at_5"] <= 1.0
            assert 0.0 <= m["precision_at_5"] <= 1.0
            assert 0.0 <= m["mrr"] <= 1.0
            assert m["mean_latency_ms"] > 0

    def test_get_cache_stats(self):
        res = client.get("/api/evaluation/cache-stats")
        assert res.status_code == 200
        stats = res.json()

        assert "cache_enabled" in stats
        assert "total_lookups" in stats
        assert "exact_hits" in stats
        assert "semantic_hits" in stats
        assert "hit_rate_pct" in stats
        assert "current_state_fingerprint" in stats

    def test_clear_cache_endpoint(self):
        # Set a test entry in cache
        cache_mgr = SemanticCacheManager.get_instance()
        cache_mgr._in_memory_cache["test_key"] = {"answer": "test"}

        res = client.post("/api/evaluation/cache-clear")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["purged_entries"] >= 1

