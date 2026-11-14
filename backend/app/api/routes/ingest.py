from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.models.schemas import IngestResponse
from app.services.ingestion import ingest_pdf

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """Upload a PDF policy document to ingest into the vector database."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Stream upload to a temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        chunks_indexed = ingest_pdf(tmp_path, document_name=file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return IngestResponse(
        status="success",
        document_name=file.filename,
        chunks_indexed=chunks_indexed,
        message=f"Successfully indexed {chunks_indexed} chunks from '{file.filename}'.",
    )

