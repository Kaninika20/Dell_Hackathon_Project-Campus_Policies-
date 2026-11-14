from __future__ import annotations

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str = ""
    gemini_embedding_model: str = "models/gemini-embedding-001"
    gemini_embedding_dim: int = 768
    gemini_generative_model: str = "models/gemini-3.5-flash-lite"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "campus_policies"

    # Ingestion constraints
    max_upload_size_bytes: int = 20 * 1024 * 1024  # 20 MB default
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # Retrieval
    top_k: int = 5
    use_hyde: bool = True

    # Caching (Redis + Semantic Caching)
    redis_url: str = "redis://localhost:6379/0"
    enable_semantic_cache: bool = True
    semantic_cache_threshold: float = 0.90
    cache_ttl_seconds: int = 86400  # 24 hours, invalidated on policy updates

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
