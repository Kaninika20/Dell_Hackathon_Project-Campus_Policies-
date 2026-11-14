from __future__ import annotations

from typing import List
import google.generativeai as genai

from app.core.config import settings


def _configure_genai() -> None:
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please add it to your .env file."
        )
    genai.configure(api_key=settings.gemini_api_key)


def get_embedding(text: str) -> List[float]:
    """Return the Gemini embedding vector for document chunk."""
    _configure_genai()
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=settings.gemini_embedding_dim,
    )
    return result["embedding"]


def get_query_embedding(text: str) -> List[float]:
    """Return the Gemini embedding vector for query string."""
    _configure_genai()
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=text,
        task_type="retrieval_query",
        output_dimensionality=settings.gemini_embedding_dim,
    )
    return result["embedding"]


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Return embeddings for a list of texts."""
    _configure_genai()
    embeddings: List[List[float]] = []
    for text in texts:
        result = genai.embed_content(
            model=settings.gemini_embedding_model,
            content=text,
            task_type="retrieval_document",
            output_dimensionality=settings.gemini_embedding_dim,
        )
        embeddings.append(result["embedding"])
    return embeddings
