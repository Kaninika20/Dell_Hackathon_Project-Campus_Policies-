from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException, status

from app.core.config import settings
from app.models.schemas import (
    IngestResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentInfo
)
from app.services.ingestion import ingest_pdf, delete_document
from app.services.document_registry import DocumentRegistry

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts PDF upload, validates file type and size, extracts text,
    performs section-aware chunking, generates embeddings, and saves to Qdrant.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents (.pdf) are supported."
        )

    # Read content to check file size
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    if file_size > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb:.1f} MB."
        )

    # Write temporarily to disk for PyMuPDF processing
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result = ingest_pdf(
            pdf_path=tmp_path,
            document_name=file.filename,
            file_size_bytes=file_size
        )
        return IngestResponse(
            status="success",
            document_id=result["document_id"],
            document_name=result["document_name"],
            chunks_indexed=result["chunks_indexed"],
            pages_count=result["pages_count"],
            message=f"Successfully ingested '{file.filename}' with {result['chunks_indexed']} sections indexed."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("", response_model=DocumentListResponse)
def list_documents():
    """Returns a list of all currently indexed policy documents."""
    registry = DocumentRegistry.get_instance()
    docs = registry.list_documents()
    return DocumentListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total_count=len(docs)
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def remove_document(document_id: str):
    """Deletes a document and purges all of its associated vector embeddings from Qdrant."""
    try:
        deleted = delete_document(document_id)
        return DocumentDeleteResponse(
            status="success",
            document_id=document_id,
            document_name=deleted["document_name"],
            message=f"Document '{deleted['document_name']}' and its vector embeddings were removed."
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )

