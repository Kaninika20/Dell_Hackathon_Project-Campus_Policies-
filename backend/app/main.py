from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import documents, chat, query, health, evaluation

app = FastAPI(
    title="CampusPolicy AI",
    description="RAG-powered university policy discovery assistant using Gemini + Qdrant.",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(query.router)
app.include_router(evaluation.router)


@app.get("/")
def root():
    return {
        "message": "CampusPolicy AI backend is running.",
        "docs_url": "/docs",
        "chat_endpoint": "/api/chat",
        "health_url": "/health"
    }
