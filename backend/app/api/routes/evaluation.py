"""
evaluation.py — Retrieval Evaluation & Cache Telemetry Router

Exposes:
  1. GET /api/evaluation/benchmark: Real measured benchmark metrics (Recall@5, Precision@5, MRR, Latency).
  2. GET /api/evaluation/cache-stats: Live cumulative exact/semantic cache telemetry & hit rates.
  3. POST /api/evaluation/cache-clear: Cache invalidation trigger.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from app.services.semantic_cache import SemanticCacheManager
from app.services.benchmark_evaluator import EVAL_DATASET, run_full_benchmark

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

BENCHMARK_FILE = Path("docs/retrieval_benchmark.json")


# ── Schemas ──────────────────────────────────────────────────────────────────

class BenchmarkMetric(BaseModel):
    mode: str
    queries_evaluated: int
    recall_at_5: float
    precision_at_5: float
    mrr: float
    mean_latency_ms: float


class EvalQueryItem(BaseModel):
    id: int
    query: str
    target_doc: str
    target_keywords: List[str]


class EvaluationResponse(BaseModel):
    benchmark_metrics: List[BenchmarkMetric]
    dataset_size: int
    sample_queries: List[EvalQueryItem]
    cache_stats: Dict[str, Any]
    notes: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/benchmark", response_model=EvaluationResponse)
def get_benchmark_results(fresh: bool = Query(False, description="Whether to trigger a fresh benchmark run")):
    """
    Returns actual measured retrieval metrics comparing Baseline, HyDE, and HyDE+Hybrid.
    Never fabricates metrics.
    """
    metrics_data = []

    if fresh:
        try:
            metrics_data = run_full_benchmark()
            BENCHMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(BENCHMARK_FILE, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Fresh benchmark run failed: {str(e)}"
            )
    else:
        # Load from disk
        if BENCHMARK_FILE.exists():
            try:
                with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
                    metrics_data = json.load(f)
            except Exception:
                metrics_data = []

        if not metrics_data:
            # Fallback to run if not exists
            metrics_data = run_full_benchmark()

    cache_stats = SemanticCacheManager.get_instance().get_stats()

    return EvaluationResponse(
        benchmark_metrics=[BenchmarkMetric(**m) for m in metrics_data],
        dataset_size=len(EVAL_DATASET),
        sample_queries=[EvalQueryItem(**q) for q in EVAL_DATASET],
        cache_stats=cache_stats,
        notes="Metrics measured on genuine sample policy documents with ground-truth target clauses."
    )


@router.get("/cache-stats")
def get_cache_statistics():
    """Returns live cumulative cache metrics."""
    return SemanticCacheManager.get_instance().get_stats()


@router.post("/cache-clear")
def clear_cache():
    """Purges all entries from semantic cache."""
    purged = SemanticCacheManager.get_instance().invalidate_all()
    return {"status": "success", "purged_entries": purged}

