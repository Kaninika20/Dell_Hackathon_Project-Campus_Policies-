from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple

import fitz  # PyMuPDF
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue, PayloadSchemaType

from app.core.config import settings
from app.core.embeddings import get_embeddings_batch
from app.core.qdrant_client import get_qdrant_client
from app.services.chunker import chunk_extracted_pages
from app.services.document_registry import DocumentRegistry
from app.services.bm25_store import BM25Store
from app.services.semantic_cache import SemanticCacheManager


def ensure_collection() -> None:
    """Create the Qdrant collection if it does not exist, and index document_id for filtering."""
    client = get_qdrant_client()
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection_name not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(
                size=settings.gemini_embedding_dim,
                distance=Distance.COSINE
            ),
        )
    try:
        client.create_payload_index(
            collection_name=settings.qdrant_collection_name,
            field_name="document_id",
            field_schema=PayloadSchemaType.KEYWORD
        )
    except Exception:
        pass


def _extract_pages_with_metadata(pdf_path: Path) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extract text, page count, and version metadata from PDF.
    Returns (pages_list, detected_version).
    """
    doc = fitz.open(str(pdf_path))
    pages: List[Dict[str, Any]] = []
    
    # Try reading doc metadata
    meta = doc.metadata or {}
    version = meta.get("subject") or meta.get("keywords") or "1.0"
    if not isinstance(version, str) or not version.strip():
        version = "1.0"

    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page_number": i, "text": text})
            
    doc.close()
    return pages, version


def ingest_pdf(pdf_path: Path, document_name: str, file_size_bytes: int) -> Dict[str, Any]:
    """
    Complete document ingestion pipeline:
    1. Check for duplicates
    2. Extract text & pages via PyMuPDF
    3. Section-aware chunking
    4. Generate Gemini embeddings
    5. Upsert points into Qdrant with all metadata fields
    6. Register in DocumentRegistry & BM25 store
    """
    registry = DocumentRegistry.get_instance()
    
    # Prevent duplicate document ingestion
    if registry.has_document(document_name):
        raise ValueError(f"Document '{document_name}' has already been indexed. Delete it first if you wish to re-upload.")

    ensure_collection()

    pages, doc_version = _extract_pages_with_metadata(pdf_path)
    if not pages:
        raise ValueError(f"File '{document_name}' contains no readable text or is empty.")

    # Section-aware chunking
    raw_chunks = chunk_extracted_pages(
        pages,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap
    )
    if not raw_chunks:
        raise ValueError(f"Could not construct text chunks from '{document_name}'.")

    document_id = str(uuid.uuid4())
    upload_timestamp = datetime.now(timezone.utc).isoformat()

    # Build full chunk records
    chunk_records: List[Dict[str, Any]] = []
    for rc in raw_chunks:
        chunk_id = str(uuid.uuid4())
        chunk_records.append({
            "chunk_id": chunk_id,
            "document_id": document_id,
            "document_name": document_name,
            "page_number": rc["page_number"],
            "section_heading": rc["section_heading"],
            "text": rc["text"],
            "upload_timestamp": upload_timestamp,
            "document_version": doc_version,
        })

    # Generate embeddings
    texts = [c["text"] for c in chunk_records]
    embeddings = get_embeddings_batch(texts)

    # Upsert to Qdrant
    client = get_qdrant_client()
    points = [
        PointStruct(
            id=c["chunk_id"],
            vector=emb,
            payload=c
        )
        for c, emb in zip(chunk_records, embeddings)
    ]
    client.upsert(
        collection_name=settings.qdrant_collection_name,
        points=points
    )

    # Update in-memory BM25 store
    bm25_store = BM25Store.get_instance()
    bm25_store.add_chunks(chunk_records)

    # Register in document registry
    doc_info = registry.register(
        document_id=document_id,
        document_name=document_name,
        chunks_count=len(chunk_records),
        pages_count=len(pages),
        file_size_bytes=file_size_bytes,
        document_version=doc_version
    )

    # Invalidate stale semantic cache entries since policy knowledge base changed
    cache_mgr = SemanticCacheManager.get_instance()
    cache_mgr.purge_stale_entries()

    return {
        "document_id": document_id,
        "document_name": document_name,
        "chunks_indexed": len(chunk_records),
        "pages_count": len(pages),
        "document_version": doc_version,
    }


def delete_document(document_id: str) -> Dict[str, Any]:
    """
    Deletes document metadata and removes all associated vectors from Qdrant.
    """
    registry = DocumentRegistry.get_instance()
    doc_info = registry.get_document(document_id)
    if not doc_info:
        raise KeyError(f"Document with ID '{document_id}' not found.")

    client = get_qdrant_client()
    
    # Filter points by document_id in payload
    client.delete(
        collection_name=settings.qdrant_collection_name,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                )
            ]
        )
    )

    # Remove from registry
    deleted_info = registry.delete_document(document_id)

    # Invalidate stale semantic cache entries since policy was deleted
    cache_mgr = SemanticCacheManager.get_instance()
    cache_mgr.purge_stale_entries()

    return deleted_info or doc_info
