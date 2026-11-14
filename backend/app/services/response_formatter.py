from __future__ import annotations

from typing import List, Dict, Any, Optional
from app.models.schemas import ChatResponse, ChatSource


def format_chat_response(
    answer: str,
    evidence_list: List[Dict[str, Any]],
    retrieval_method: str = "baseline",
    confidence: Optional[float] = None,
    retrieval_metadata: Optional[Dict[str, Any]] = None
) -> ChatResponse:
    """
    Constructs the standardized ChatResponse across all retrieval modes.
    Does not fabricate confidence scores; returns None unless a validated metric exists.
    """
    sources: List[ChatSource] = [
        ChatSource(
            document_name=item["document_name"],
            page_number=item["page_number"],
            section_heading=item["section_heading"],
            excerpt=item["excerpt"]
        )
        for item in evidence_list
    ]

    return ChatResponse(
        answer=answer,
        sources=sources,
        retrieval_method=retrieval_method,
        confidence=confidence,
        retrieval_metadata=retrieval_metadata
    )
