import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.document_registry import DocumentRegistry

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_policy_documents():
    """Ensure policies are indexed for retrieval mode comparison tests."""
    reg = DocumentRegistry.get_instance()
    reg._documents.clear()
    reg._filename_map.clear()

    policy1 = Path("data/sample_policies/SAMPLE_Academic_Integrity_Policy.pdf")
    policy2 = Path("data/sample_policies/SAMPLE_Attendance_And_Leave_Rules.pdf")

    assert policy1.exists() and policy2.exists(), "Sample policies must exist."

    with open(policy1, "rb") as f1:
        res1 = client.post(
            "/api/documents/upload",
            files={"file": (policy1.name, io.BytesIO(f1.read()), "application/pdf")}
        )
        assert res1.status_code == 201

    with open(policy2, "rb") as f2:
        res2 = client.post(
            "/api/documents/upload",
            files={"file": (policy2.name, io.BytesIO(f2.read()), "application/pdf")}
        )
        assert res2.status_code == 201

    yield


def test_baseline_mode():
    """Test retrieval_method='baseline'."""
    res = client.post("/api/chat", json={
        "question": "What is the penalty for first-time plagiarism?",
        "retrieval_method": "baseline"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["retrieval_method"] == "baseline"
    assert data["retrieval_metadata"]["retrieval_method"] == "baseline"
    assert data["retrieval_metadata"]["hypothetical_passage"] is None
    assert len(data["sources"]) > 0


def test_hyde_mode():
    """Test retrieval_method='hyde' generates hypothetical excerpt for retrieval but returns actual docs."""
    res = client.post("/api/chat", json={
        "question": "Can I skip college for a week if I am sick?",
        "retrieval_method": "hyde"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["retrieval_method"] == "hyde"
    meta = data["retrieval_metadata"]
    assert meta["retrieval_method"] == "hyde"
    assert meta["hypothetical_passage"] is not None
    assert len(meta["hypothetical_passage"]) > 10
    # The actual sources presented to the student MUST be real documents, NOT the hypothetical passage
    assert len(data["sources"]) > 0
    for s in data["sources"]:
        assert s["document_name"].endswith(".pdf")
        assert s["page_number"] >= 1


def test_hyde_hybrid_mode():
    """Test retrieval_method='hyde_hybrid' runs HyDE + BM25 + Reciprocal Rank Fusion."""
    res = client.post("/api/chat", json={
        "question": "How do I appeal an academic integrity sanction?",
        "retrieval_method": "hyde_hybrid"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["retrieval_method"] == "hyde_hybrid"
    meta = data["retrieval_metadata"]
    assert meta["retrieval_method"] == "hyde_hybrid"
    assert meta["hypothetical_passage"] is not None
    assert meta["latency_ms"] > 0
    assert len(data["sources"]) > 0
    # Response contains grounded answer and citations
    assert any("academic review board" in data["answer"].lower() or "appeal" in data["answer"].lower() for _ in [1])

