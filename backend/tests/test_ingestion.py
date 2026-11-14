import os
import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.qdrant_client import get_qdrant_client
from app.services.document_registry import DocumentRegistry

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Ensure clean registry before tests."""
    reg = DocumentRegistry.get_instance()
    reg._documents.clear()
    reg._filename_map.clear()
    yield


def test_upload_invalid_file_type():
    """Verify non-PDF uploads are rejected."""
    fake_txt = io.BytesIO(b"Hello world this is a text file")
    response = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", fake_txt, "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PDF documents (.pdf) are supported" in response.json()["detail"]


def test_upload_empty_pdf():
    """Verify 0-byte upload is rejected."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", empty_file, "application/pdf")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_and_delete_valid_multipage_pdf():
    """
    Test uploading a multi-page PDF:
    - Verifies extraction of page numbers & section headings
    - Verifies Qdrant vector storage
    - Verifies listing via GET /api/documents
    - Verifies deletion via DELETE /api/documents/{id}
    - Verifies duplicate detection
    """
    sample_pdf = Path("data/sample_policies/SAMPLE_Academic_Integrity_Policy.pdf")
    assert sample_pdf.exists(), "Sample PDF must exist for this test"

    with open(sample_pdf, "rb") as f:
        file_bytes = f.read()

    # 1. Upload
    response = client.post(
        "/api/documents/upload",
        files={"file": ("SAMPLE_Academic_Integrity_Policy.pdf", io.BytesIO(file_bytes), "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    doc_id = data["document_id"]
    assert data["pages_count"] >= 2  # Multi-page test
    assert data["chunks_indexed"] > 0

    # 2. Duplicate detection
    dup_res = client.post(
        "/api/documents/upload",
        files={"file": ("SAMPLE_Academic_Integrity_Policy.pdf", io.BytesIO(file_bytes), "application/pdf")}
    )
    assert dup_res.status_code == 422
    assert "already been indexed" in dup_res.json()["detail"]

    # 3. List documents
    list_res = client.get("/api/documents")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_count"] == 1
    assert list_data["documents"][0]["document_id"] == doc_id

    # 4. Check Qdrant points
    qdrant = get_qdrant_client()
    points, _ = qdrant.scroll(
        collection_name=settings.qdrant_collection_name,
        limit=10,
        with_payload=True
    )
    assert len(points) > 0
    # Check required metadata fields in points
    sample_point = points[0]
    payload = sample_point.payload
    for key in ["chunk_id", "document_id", "document_name", "page_number", "section_heading", "text", "upload_timestamp", "document_version"]:
        assert key in payload, f"Missing payload key: {key}"

    # 5. Delete document and confirm vector cleanup
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Confirm list is now 0
    list_after = client.get("/api/documents")
    assert list_after.json()["total_count"] == 0

