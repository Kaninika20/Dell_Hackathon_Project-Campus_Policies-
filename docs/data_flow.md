# Data Flow & Lifecycle Specifications

This document outlines the detailed sequence and data transformations across the two primary operational pipelines in CampusPolicy AI: **Document Ingestion** and **Grounded Chat Inference**.

---

## 1. Document Ingestion Pipeline

The document ingestion pipeline transforms raw university policy PDFs into structured, section-aware vector embeddings stored in Qdrant and indexed for keyword search in BM25.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin / Demo User
    participant UI as React UI (DocumentManager)
    participant API as FastAPI (/api/documents/upload)
    participant Parser as PyMuPDF Extractor
    participant Chunker as Section-Aware Chunker
    participant Registry as Document Registry
    participant Embedder as Gemini Embedding API
    participant Qdrant as Qdrant Cloud DB
    participant BM25 as In-Memory BM25 Store

    Admin->>UI: Select / Drop PDF handbook
    UI->>API: POST multipart/form-data (file)
    API->>API: Validate file format (.pdf) and size (< 20MB)
    API->>Parser: Extract text, page numbers, metadata
    Parser-->>API: List of {page_number, text}
    
    API->>Chunker: chunk_extracted_pages(pages, chunk_size=1000, overlap=150)
    Note over Chunker: Detects section headings & preserves policy boundaries
    Chunker-->>API: List of raw chunks with section headings
    
    API->>Registry: Generate document_id, check duplicates
    API->>Embedder: get_embeddings_batch(texts, dim=768)
    Embedder-->>API: List of 768-dim float vectors
    
    API->>Qdrant: Upsert points (vector + payload metadata)
    Note over Qdrant: Stores chunk_id, document_id, document_name,<br/>page_number, section_heading, text, version
    Qdrant-->>API: Upsert confirmation
    
    API->>BM25: add_chunks(chunk_records)
    API->>Registry: register(doc_info)
    API-->>UI: 201 Created (document_id, chunks_indexed, pages_count)
    UI-->>Admin: Display green status and update document list
```

---

## 2. Multi-Mode Chat & Retrieval Pipeline

The query pipeline handles informal student questions, executes query expansion via HyDE, retrieves candidate evidence chunks via hybrid fusion, evaluates guardrails, and generates a grounded response with citations.

```mermaid
sequenceDiagram
    autonumber
    actor Student as Student User
    participant UI as React UI (ChatDashboard)
    participant API as FastAPI (/api/chat)
    participant Guardrails as Prompt Injection Guard
    participant HyDE as HyDE Generator (Gemini)
    participant Embedder as Gemini Embedding API
    participant Qdrant as Qdrant Cloud DB
    participant BM25 as BM25 Keyword Store
    participant RRF as Reciprocal Rank Fusion
    participant Generator as Gemini Generative Model (3.5 Flash Lite)

    Student->>UI: Enters query ("Can I skip college if I am sick?")
    UI->>API: POST /api/chat {question, retrieval_method: "hyde_hybrid"}
    
    API->>Guardrails: sanitise_user_query(question)
    Note over Guardrails: Strips override tokens (e.g. DAN, ignore instructions)
    Guardrails-->>API: sanitised_question, injection_detected_flag

    rect rgb(230, 255, 230)
        Note over API, Embedder: Semantic Caching Layer (Extension A)
        API->>API: Exact Query Cache Check O(1)
        opt Exact Cache Hit
            API-->>UI: Instant 200 OK (< 10ms, cached=true, type="exact")
        end
        API->>Embedder: get_query_embedding(sanitised_question)
        Embedder-->>API: query_vector
        API->>API: Semantic Cache Check (Cosine Sim >= 0.90)
        opt Semantic Cache Hit
            API-->>UI: Instant 200 OK (< 50ms, cached=true, type="semantic")
        end
    end
    
    rect rgb(240, 248, 255)
        Note over API, RRF: Parallel Retrieval Branching (hyde_hybrid mode on cache miss)
        API->>HyDE: generate_hypothetical_document(sanitised_question)
        HyDE-->>API: Formal administrative policy excerpt (retrieval artifact)
        
        API->>Embedder: get_query_embedding(hypo_passage, dim=768)
        Embedder-->>API: 768-dim hypothetical query vector
        
        API->>Qdrant: Search top-10 chunks by hypothetical vector
        Qdrant-->>API: Dense candidate chunk list
        
        API->>BM25: Search top-10 chunks by query keywords
        BM25-->>API: Sparse candidate chunk list
        
        API->>RRF: reciprocal_rank_fusion([dense_chunks, sparse_chunks], k=60)
        RRF-->>API: Final Top-K actual policy chunks (ranked by RRF score)
    end

    API->>Guardrails: sanitise_chunk_text(chunks) + check versions & conflicts
    Note over Guardrails: Verifies document validity and scrubs chunk injections
    Guardrails-->>API: clean_context_string, validated_evidence_list, version_warning
    
    API->>Generator: generate_grounded_answer(question, clean_context)
    Note over Generator: Strict prompt: Ground only in retrieved policy clauses.<br/>Correct false premises. Cite document name & page.
    Generator-->>API: Synthesized grounded answer
    
    API->>API: Prepend version warning (if applicable) & format ChatResponse
    API-->>UI: 200 OK (answer, sources, retrieval_method, retrieval_metadata)
    UI-->>Student: Render formatted answer + expandable citation cards
```

