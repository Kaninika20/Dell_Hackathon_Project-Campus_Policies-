from __future__ import annotations

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Document Schemas
# ---------------------------------------------------------------------------

class DocumentInfo(BaseModel):
    document_id: str
    document_name: str
    chunks_count: int
    pages_count: int
    file_size_bytes: int
    document_version: str = "1.0"
    validity_status: str = "current"
    effective_academic_year: str = "AY 2025-26"
    upload_timestamp: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total_count: int


class DocumentDeleteResponse(BaseModel):
    status: str
    document_id: str
    document_name: str
    message: str


class IngestResponse(BaseModel):
    status: str
    document_id: str
    document_name: str
    chunks_indexed: int
    pages_count: int
    message: str = ""


# ---------------------------------------------------------------------------
# Chat & Hybrid RAG Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="The user's policy inquiry.")
    retrieval_method: Optional[str] = Field(
        default="baseline",
        description="Retrieval mode: 'baseline', 'hyde', or 'hyde_hybrid'"
    )
    top_k: Optional[int] = Field(default=None, ge=1, le=20, description="Number of evidence chunks to retrieve.")


class ChatSource(BaseModel):
    document_name: str
    page_number: int
    section_heading: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource]
    retrieval_method: str = "baseline"
    confidence: Optional[float] = None
    retrieval_metadata: Optional[Dict[str, Any]] = None


# Legacy query schema compatibility
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class SourceChunk(BaseModel):
    document_name: str
    page_number: int
    section_heading: str
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    question: str


# ---------------------------------------------------------------------------
# Health Schema
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    qdrant_ok: bool = False
    gemini_configured: bool = False
    redis_available: bool = False
    cache_enabled: bool = True
