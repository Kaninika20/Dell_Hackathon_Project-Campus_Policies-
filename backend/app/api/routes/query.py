from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import QueryRequest, QueryResponse
from app.services.retrieval import hybrid_retrieve_and_answer

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_policies(request: QueryRequest):
    """Ask a question about university policies."""
    try:
        response = hybrid_retrieve_and_answer(
            question=request.question,
            top_k=request.top_k,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

