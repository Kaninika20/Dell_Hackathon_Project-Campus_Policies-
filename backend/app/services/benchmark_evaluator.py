from __future__ import annotations

import time
import json
from pathlib import Path
from typing import List, Dict, Any

from app.services.hybrid_retrieval import multi_mode_retrieve
from app.services.ingestion import ingest_pdf
from app.services.document_registry import DocumentRegistry

# 16 Evaluation questions grounded in the 2 sample policy documents:
# - SAMPLE_Academic_Integrity_Policy.pdf
# - SAMPLE_Attendance_And_Leave_Rules.pdf
EVAL_DATASET = [
    {
        "id": 1,
        "query": "Can I skip college for a week if I am sick?",
        "target_doc": "SAMPLE_Attendance_And_Leave_Rules.pdf",
        "target_keywords": ["condonation", "medical grounds", "65%", "74%"]
    },
    {
        "id": 2,
        "query": "What is the minimum attendance required to write final exams?",
        "target_doc": "SAMPLE_Attendance_And_Leave_Rules.pdf",
        "target_keywords": ["seventy-five percent", "75%", "minimum attendance"]
    },
    {
        "id": 3,
        "query": "Who is authorized to condone low attendance?",
        "target_doc": "SAMPLE_Attendance_And_Leave_Rules.pdf",
        "target_keywords": ["Dean of Student Affairs", "condoned", "medical"]
    },
    {
        "id": 4,
        "query": "What happens if my attendance drops below 65 percent?",
        "target_doc": "SAMPLE_Attendance_And_Leave_Rules.pdf",
        "target_keywords": ["detained", "sixty-five percent", "re-register"]
    },
    {
        "id": 5,
        "query": "How many days do I have to submit my medical certificate?",
        "target_doc": "SAMPLE_Attendance_And_Leave_Rules.pdf",
        "target_keywords": ["three (3) days", "resuming classes", "medical practitioner"]
    },
    {
        "id": 6,
        "query": "Is using ChatGPT for homework considered cheating or plagiarism?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["artificial intelligence", "unauthorized collaboration", "Subsection 2.4"]
    },
    {
        "id": 7,
        "query": "How does the university define plagiarism?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["definition of plagiarism", "submission", "reproduction", "citation"]
    },
    {
        "id": 8,
        "query": "How long does a professor have to notify a student of misconduct?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["five (5) academic working days", "investigation procedures"]
    },
    {
        "id": 9,
        "query": "What punishment is given for a first time minor cheating offense?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["minor first-time", "reprimand", "grade of zero"]
    },
    {
        "id": 10,
        "query": "Can I get suspended for repeating academic dishonesty?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["repeated violations", "suspension", "Grade XF"]
    },
    {
        "id": 11,
        "query": "Where do I submit an appeal if I disagree with an integrity penalty?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["Academic Review Board", "appeals process"]
    },
    {
        "id": 12,
        "query": "What is the deadline to appeal an integrity violation ruling?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["ten (10) calendar days", "appeals process"]
    },
    {
        "id": 13,
        "query": "Are lab evaluations covered under the honor code?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["laboratory assignments", "purpose and applicability"]
    },
    {
        "id": 14,
        "query": "Can I paraphrase someone else's paper without citing them?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["paraphrasing without proper attribution", "plagiarism"]
    },
    {
        "id": 15,
        "query": "What are the allowed legal reasons to appeal a disciplinary sanction?",
        "target_doc": "SAMPLE_Academic_Integrity_Policy.pdf",
        "target_keywords": ["procedural irregularity", "disproportionate", "newly discovered"]
    },
    {
        "id": 16,
        "query": "Do I have to re-take a course if I am detained for low attendance?",
        "target_doc": "SAMPLE_Attendance_And_Leave_Rules.pdf",
        "target_keywords": ["re-register the course", "subsequent academic cycle"]
    }
]


def evaluate_retrieval_mode(mode: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Evaluates a specific retrieval mode over the benchmark dataset.
    Calculates:
      - Recall@5
      - Precision@5
      - MRR (Mean Reciprocal Rank)
      - Mean Latency (ms)
    """
    total_queries = len(EVAL_DATASET)
    recalls: List[float] = []
    precisions: List[float] = []
    reciprocal_ranks: List[float] = []
    latencies: List[float] = []

    for item in EVAL_DATASET:
        q = item["query"]
        target_doc = item["target_doc"]
        target_kw = [k.lower() for k in item["target_keywords"]]

        start = time.perf_counter()
        chunks, meta = multi_mode_retrieve(q, method=mode, top_k=top_k)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)

        # A chunk is considered relevant if it matches the target document and any key target clause
        relevant_retrieved = 0
        first_relevant_rank = None

        for rank, c in enumerate(chunks, start=1):
            text_lower = c["text"].lower()
            doc_matches = (c["document_name"] == target_doc)
            kw_matches = any(kw in text_lower for kw in target_kw)

            if doc_matches and kw_matches:
                relevant_retrieved += 1
                if first_relevant_rank is None:
                    first_relevant_rank = rank

        # Precision@K = (relevant retrieved) / K
        precisions.append(relevant_retrieved / top_k)
        # Recall@K = (relevant retrieved > 0) -> Binary relevant passage retrieval for target clause
        recalls.append(1.0 if relevant_retrieved > 0 else 0.0)
        # Reciprocal Rank = 1 / first_relevant_rank if found else 0
        reciprocal_ranks.append(1.0 / first_relevant_rank if first_relevant_rank else 0.0)

    return {
        "mode": mode,
        "queries_evaluated": total_queries,
        "recall_at_5": round(sum(recalls) / total_queries, 4),
        "precision_at_5": round(sum(precisions) / total_queries, 4),
        "mrr": round(sum(reciprocal_ranks) / total_queries, 4),
        "mean_latency_ms": round(sum(latencies) / total_queries, 2),
    }


def run_full_benchmark() -> List[Dict[str, Any]]:
    # Ingest sample policies if registry is empty
    reg = DocumentRegistry.get_instance()
    p1 = Path("data/sample_policies/SAMPLE_Academic_Integrity_Policy.pdf")
    p2 = Path("data/sample_policies/SAMPLE_Attendance_And_Leave_Rules.pdf")
    if not reg.has_document(p1.name):
        ingest_pdf(p1, p1.name, p1.stat().st_size)
    if not reg.has_document(p2.name):
        ingest_pdf(p2, p2.name, p2.stat().st_size)

    results = []
    modes = ["baseline", "hyde", "hyde_hybrid"]
    for m in modes:
        print(f"Benchmarking mode: {m}...")
        res = evaluate_retrieval_mode(m, top_k=5)
        results.append(res)
        print(f"  Recall@5: {res['recall_at_5']}, Precision@5: {res['precision_at_5']}, MRR: {res['mrr']}, Latency: {res['mean_latency_ms']} ms")

    return results


if __name__ == "__main__":
    benchmark_results = run_full_benchmark()
    out_file = Path("docs/retrieval_benchmark.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)
    print(f"\nBenchmark completed and saved to {out_file}")

