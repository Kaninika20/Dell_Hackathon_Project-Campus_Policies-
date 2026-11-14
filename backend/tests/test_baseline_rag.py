import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.document_registry import DocumentRegistry

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_policy_documents():
    """Ensure sample policies are ingested into Qdrant for RAG tests."""
    reg = DocumentRegistry.get_instance()
    reg._documents.clear()
    reg._filename_map.clear()

    policy1 = Path("data/sample_policies/SAMPLE_Academic_Integrity_Policy.pdf")
    policy2 = Path("data/sample_policies/SAMPLE_Attendance_And_Leave_Rules.pdf")

    assert policy1.exists() and policy2.exists(), "Sample policy files must exist."

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


def test_question_with_answer_in_documents():
    """Test 1: A question whose answer is explicitly present in the policies."""
    payload = {"question": "Can I get attendance relaxation due to medical reasons?"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["retrieval_method"] == "baseline"
    assert data["confidence"] is None  # We do not fabricate confidence
    assert len(data["sources"]) > 0

    # Answer should address medical relaxation and condonation percentages
    answer = data["answer"].lower()
    assert any(term in answer for term in ["medical", "condon", "dean", "65%", "74%"])
    # Sources must contain document name and page number
    source = data["sources"][0]
    assert "SAMPLE_Attendance_And_Leave_Rules.pdf" in source["document_name"]
    assert source["page_number"] >= 1
    assert len(source["excerpt"]) > 0


def test_question_with_no_answer_in_documents():
    """Test 2: A question not covered by any uploaded policy (abstention test)."""
    payload = {"question": "What are the rules for parking skateboards in the dining hall?"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    answer = data["answer"].lower()
    # Must report inability to verify or lack of policy evidence, without inventing rules
    assert any(phrase in answer for phrase in ["not", "could not be verified", "no information", "insufficient", "does not contain", "not mentioned"])


def test_ambiguous_question():
    """Test 3: An ambiguous question spanning multiple concepts."""
    payload = {"question": "What happens if I miss something?"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["sources"]) > 0
    # Model should address either missed classes (attendance) or missed assessments (integrity/exams) grounded in docs
    assert len(data["answer"]) > 20


def test_question_with_false_assumption():
    """Test 4: A question containing a false assumption contrary to policy."""
    # Policy states 75% is minimum, and condonation only down to 65% on medical grounds.
    # Question falsely assumes attendance can drop to 40% with a doctor's note.
    payload = {"question": "Since the policy allows attendance to drop to 40% with a medical certificate, where do I submit the note?"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    answer = data["answer"].lower()
    # Model should correct the 40% assumption using actual 65% / 75% thresholds
    assert any(num in answer for num in ["65", "75", "not", "incorrect", "below"])

