# CampusPolicy AI — Development & Prompt Log

This document provides a chronological record of the development prompts, model selections, architectural decisions, modifications, and debugging breakthroughs throughout the creation of **CampusPolicy AI**.

---

## Phase 0 — Project Initialization & Architecture

* **Model Used:** Current IDE Model (Gemini 2.5 Pro)
* **User Goal:** Set up initial modular folder structure, environment configurations, and architectural plans for an 8–9 hour MVP.
* **Key Prompt Excerpt:**
  > *"Act as a senior software architect. We are building CampusPolicy AI... Design a simple, modular project architecture. Create separate frontend and backend directories. Create initial folder structure. Prepare .env.example, README.md, PROMPT_LOG.md, and docs/architecture.md."*
* **Implementations & Decisions:**
  * Scaffolded `frontend/` (React + Vite + Tailwind v4) and `backend/` (FastAPI + Python 3.13).
  * Designed Qdrant payload schema with `document_id`, `chunk_id`, `page_number`, `section_heading`, `text`, `upload_timestamp`, and `document_version`.
  * Formulated non-hardcoded configuration using `pydantic-settings`.

---

## Phase 1 — PDF Document Ingestion & Vector Database

* **Model Used:** Claude Sonnet 4.6 (Thinking)
* **User Goal:** Build complete document ingestion pipeline with PyMuPDF, section-aware chunking, Gemini embeddings, and Qdrant vector storage.
* **Key Prompt Excerpt:**
  > *"Implement the complete document ingestion pipeline. Accept PDF uploads, validate file type and size. Extract text using PyMuPDF... Implement section-aware chunking... Generate embeddings using the Gemini embedding API. Store vectors in Qdrant... Implement document listing and deletion endpoints."*
* **Debugging & Discoveries:**
  * **Model Deprecation Fix:** `models/text-embedding-004` was unavailable for new API keys. Switched to `models/gemini-embedding-001` configured with `output_dimensionality=768` (Matryoshka representation) to match vector dimensions and improve latency.
  * **Qdrant Payload Index:** Resolved 400 Bad Request on deletion by adding `client.create_payload_index(field_name="document_id", field_schema=PayloadSchemaType.KEYWORD)`.
  * **Testing:** Verified with unit test suite (`backend/tests/test_ingestion.py`), passing all 3 tests in 14.4s.

---

## Phase 2 — Baseline RAG Backend

* **Model Used:** Claude Sonnet 4.6 (Thinking)
* **User Goal:** Implement standard dense vector search baseline pipeline before introducing HyDE or hybrid search.
* **Key Prompt Excerpt:**
  > *"Implement the baseline RAG pipeline before adding HyDE... Receive the user's question, generate an embedding, search Qdrant, retrieve top chunks, construct context, send to Gemini, and generate a grounded answer with citations... Do not fabricate confidence scores."*
* **Implementations & Decisions:**
  * Created `retrieval_service.py`, `context_builder.py`, `generator_service.py`, and `response_formatter.py`.
  * Discovered `gemini-1.5-flash` was deprecated and `gemini-3.8-flash` had high demand throttling; standardized on `models/gemini-3.5-flash-lite` for reliable sub-2s generation.
  * Strict prompt instructions: forbid rule extrapolation, require citations (`[Document Name, Page X]`), enforce abstention on missing evidence, and refute false assumptions.
  * Verified all 4 baseline RAG test cases in `backend/tests/test_baseline_rag.py`.

---

## Phase 3 — HyDE & Hybrid Retrieval

* **Model Used:** Claude Sonnet 4.6 (Thinking)
* **User Goal:** Implement Hypothetical Document Embeddings (HyDE), BM25 keyword search, and Reciprocal Rank Fusion (RRF).
* **Key Prompt Excerpt:**
  > *"Implement HyDE (Hypothetical Document Embeddings)... Generate a hypothetical policy-style passage with Gemini... Embed passage and search Qdrant... Combine semantic similarity results with BM25 keyword results using Reciprocal Rank Fusion (RRF)... Create an evaluation dataset of 15-20 questions and measure Recall@5, Precision@5, MRR, Latency."*
* **Implementations & Decisions:**
  * Built `hyde_service.py`: Generates formal policy-style passages from colloquial queries; strictly treats hypothetical drafts as retrieval aids (never displayed as factual evidence).
  * Built `hybrid_retrieval.py`: Implemented multi-mode retrieval (`baseline`, `hyde`, `hyde_hybrid`) and Reciprocal Rank Fusion ($k=60$).
  * Built `benchmark_evaluator.py`: 16-query evaluation dataset. Real benchmark measured:
    * `baseline`: Recall@5 = 0.9375, Latency = 1795ms
    * `hyde`: Recall@5 = 0.875, Latency = 3173ms
    * `hyde_hybrid`: Recall@5 = 1.0, Latency = 2560ms

---

## Phase 4 — Guardrails & Policy Reliability

* **Model Used:** Claude Sonnet 4.6 (Thinking) & Gemini 3.8 Flash
* **User Goal:** Implement defense-in-depth policy grounding, prompt injection defenses, version validity warnings, and false premise handling.
* **Key Prompt Excerpt:**
  > *"Implement robust policy-grounding mechanisms. The most important requirement is preventing fabricated or unsupported university policies... Scenarios: Valid policy question, Fake policy introduced by user, No matching policy, Outdated policy, Conflicting policies, Prompt injection, API failure, Malicious uploads."*
* **Implementations & Decisions:**
  * Created `backend/app/services/guardrails.py`:
    * `sanitise_user_query`: Redacts injection directives (DAN, role-playing, instruction overrides).
    * `sanitise_chunk_text`: Strips embedded adversarial instructions inside ingested PDF text.
    * `classify_document_version` & `build_version_warning`: Prepends warning banners when documents are superseded or ambiguous.
    * `detect_policy_conflicts`: Identifies overlapping clauses across distinct handbooks.
  * Developed `backend/tests/test_guardrails.py` with 25 passing unit test cases.

---

## Phase 5 — React Frontend

* **Model Used:** Gemini 3.8 Flash
* **User Goal:** Build a responsive academic SaaS interface for policy exploration and document management.
* **Key Prompt Excerpt:**
  > *"Build a clean, professional and responsive frontend. Academic SaaS design: white/neutral backgrounds, dark navy text, restrained blue accents... Required screens: Main chat dashboard, Document management/upload section, Source citation panel, Basic retrieval comparison section."*
* **Implementations & Decisions:**
  * Built `DocumentManager.jsx`: Drag-and-drop PDF upload target, real-time extraction status, and document inventory with clause counts and delete buttons.
  * Built `RetrievalSelector.jsx`: Interactive toggle between `Baseline`, `HyDE`, and `HyDE + Hybrid`, with live telemetry and hypothetical passage inspection.
  * Built `CitationPanel.jsx`: Expandable citation cards with document name, page number, section heading, and exact text excerpts.
  * Built `ChatDashboard.jsx`: Chat stream, starter question pills, and Markdown answers.
  * Built `StatusBar.jsx`: Real-time connectivity monitor for FastAPI, Qdrant, and Gemini.
  * Verified Vite build: 179 modules compiled in 1.48s with 0 errors.

---

## Phase 6 — Integration, Testing & Performance

* **Model Used:** Gemini 3.8 Flash
* **User Goal:** Perform end-to-end integration testing and live performance profiling without fabricating metrics.
* **Key Prompt Excerpt:**
  > *"Act as a senior QA engineer. Test the entire application from document upload to final answer... Measure PDF ingestion time, retrieval latency, LLM generation latency, total response latency. Do not claim a sub-3-second response unless measured. Identify bottlenecks."*
* **Implementations & Decisions:**
  * Created `backend/tests/test_integration_e2e.py` covering all 5 test suites.
  * Execution Result: **16 out of 16 tests passed (100% pass rate)**.
  * **Measured Real Performance:**
    * Ingestion: ~5.3s to 5.8s per multi-page handbook.
    * Baseline Vector Retrieval: **2,697 ms** (Sub-3-second verified).
    * HyDE Vector Retrieval: **4,772 ms** (Double LLM call).
    * HyDE + Hybrid (RRF): **4,064 ms**.
  * Published formal testing report at `docs/test_report.md` and `docs/testing_report.md`.

---

## Phase 7 — Final Documentation & Demo

* **Model Used:** Gemini 3.8 Flash
* **User Goal:** Prepare final submission documentation and demo guide.
* **Deliverables Generated:**
  * `README.md` — Comprehensive project guide with architecture and setup instructions.
  * `docs/architecture.md` — Mermaid architecture topology and component boundaries.
  * `docs/data_flow.md` — Sequence diagrams for ingestion and hybrid retrieval inference.
  * `docs/technology_choices.md` — Detailed technical rationales for model, vector DB, and fusion choices.
  * `docs/testing_report.md` — Consolidated QA test report and performance profile.
  * `PROMPT_LOG.md` — Chronological prompt and engineering audit trail.
  * `.env.example` — Sanitized configuration template.


---

## Extension A — Semantic Caching (Redis + Memory Fallback) ✅

**Date:** 2026-11-14
**Model used:** Gemini 3.8 Flash

### Implementations & Architectural Decisions:
1. **Redis Integration & Transparent Fallback (`backend/app/services/semantic_cache.py`):**
   - Installed `redis>=5.0.0` with explicit justification for distributed high-speed caching.
   - Built `SemanticCacheManager`: connects to Redis via `REDIS_URL`, with an automated thread-safe in-memory cache and vector index fallback if Redis is unreachable.
2. **Exact & Semantic Similarity Lookup:**
   - **Exact Cache:** Normalized query hash $\mathcal{O}(1)$ lookup under the active knowledge base state (< 10ms response time).
   - **Semantic Cache:** Evaluates cosine similarity of the incoming query embedding against cached query embeddings under the same retrieval mode. When similarity $\ge 0.90$, returns the cached grounded response and citations without redundant Gemini LLM generation (< 50ms response time).
3. **State & Version-Aware Invalidation:**
   - Generated deterministic `state_fingerprint` in `DocumentRegistry` based on indexed document IDs, versions, and timestamps.
   - All cache keys embed the state fingerprint (`cp:cache:{state_fingerprint}:{method}:{hash}`).
   - Uploading a new document or deleting an existing policy immediately alters the fingerprint and purges stale cache keys, guaranteeing that answers based on outdated policies are never returned.
4. **API & UI Observability:**
   - Added cache telemetry (`cached: bool`, `cache_type: "exact" | "semantic"`, `similarity_score`) to `POST /api/chat` response metadata.
   - Updated `GET /health` with `redis_available` and `cache_enabled` fields.
   - Updated `StatusBar.jsx` and `RetrievalSelector.jsx` with real-time cache hit badges (`⚡ Exact` / `⚡ Semantic (94%)`).
5. **Testing & Verification (`backend/tests/test_semantic_cache.py`):**
   - 9 automated test cases passing (4 unit + 5 integration), verifying exact matches, semantic matches for paraphrased student questions, isolation across retrieval modes, and state-aware invalidation on both upload and deletion.


---

## Extension B — Model Context Protocol (MCP) Integration ✅

**Date:** 2026-11-14
**Model used:** Gemini 3.8 Flash

### Implementations & Architectural Decisions:
1. **MCP 2.x Server Implementation (`backend/app/mcp_server.py`):**
   - Built a compliant Model Context Protocol (MCP) server named `campuspolicy-ai` operating over standard stdio JSON-RPC 2.0.
   - Connected directly to `DocumentRegistry`, `multi_mode_retrieve()`, and Qdrant Cloud.
2. **Exposed Tools:**
   - **`search_policy`:** Accepts `query`, `retrieval_method`, and `top_k`. Evaluates prompt injection guardrails, executes hybrid dense + BM25 retrieval, and returns authentic policy clauses with document names, page numbers, and section headings. Never fabricates answers.
   - **`get_policy_document`:** Accepts `document_id_or_name`. Queries `DocumentRegistry` and scrolls Qdrant for all structured clauses belonging to that handbook, returning a complete section-by-section breakdown.
   - **`list_available_policies`:** Discovers all currently indexed handbooks, returning document IDs, filenames, page counts, clause counts, and validity versions.
3. **Testing & Verification (`backend/tests/test_mcp.py`):**
   - 9 automated test cases passing (100% pass rate in 24.3s), validating tool discovery, inventory listing, clause retrieval from Qdrant, prompt injection sanitization inside MCP queries, and empty query parameter validation.


---

## Post-MVP Enhancement 2 — Retrieval Evaluation & Cache Telemetry Dashboard ✅

**Date:** 2026-11-14
**Model used:** Gemini 3.8 Flash

### Implementations & Architectural Decisions:
1. **Evaluation & Telemetry Router (`backend/app/api/routes/evaluation.py`):**
   * `GET /api/evaluation/benchmark`: Exposes actual measured Recall@5, Precision@5, MRR, and Latency comparing Baseline, HyDE, and HyDE+Hybrid across the 16 ground-truth queries. Never fabricates benchmark values.
   * `GET /api/evaluation/cache-stats`: Exposes live cumulative lookups, exact hits, semantic hits, misses, hit rate percentage, and latency time saved.
   * `POST /api/evaluation/cache-clear`: Purges cache entries on command.
2. **Interactive React Evaluation Dashboard (`frontend/src/components/EvaluationDashboard.jsx`):**
   * Comparative retrieval metric table with visual progress indicators.
   * Real-time Semantic Cache Telemetry card showing hit rates and avoided LLM call latency.
   * Ground-truth evaluation dataset explorer displaying target documents and policy clauses.
3. **App Header Switcher (`frontend/src/App.jsx`):**
   * Added responsive view switcher toggling between **Policy Assistant** chat and **Retrieval Evaluation** dashboard on both desktop and mobile screens.
4. **Verification & Testing (`backend/tests/test_evaluation_api.py`):**
   * All 3 evaluation tests passing in 8.09s.
   * Vite frontend build verified cleanly (180 modules in 878ms).


---

## Post-MVP Standout Enhancements & Document Freshness ✅

**Date:** 2026-11-14
**Model used:** Gemini 3.8 Flash

### Implementations & Architectural Decisions:
1. **Interactive Guardrail & Stress-Test Arena (`frontend/src/components/ChatDashboard.jsx`):**
   * Built live one-click adversarial test presets directly into the UI:
     * *Prompt Injection Attack:* Demonstrates pattern redaction (DAN / instruction overrides) and strict policy grounding.
     * *False Premise / Rumor Refutation:* Rebuts unverified 40% attendance claims using the official Dean condonation threshold.
     * *Out-of-Scope Hallucination Trap:* Asserts verified abstention when asked about scooter speeds in dining halls.
     * *Sub-50ms Semantic Cache Benchmark:* Demonstrates latency drop from ~3,000ms to < 50ms upon query repetition.
2. **Document Freshness & Validity Lifecycle (`backend/app/services/document_registry.py`, `backend/app/services/guardrails.py`):**
   * Added `validity_status` (`current`, `superseded`, `expired`, `unknown`) and `effective_academic_year` metadata fields.
   * Document List in sidebar displays live status pills: `Active (AY 2025-26)`, `Superseded`, `Expired`, and `Cycle Unconfirmed`.
   * Citing older or superseded documents automatically prepends an explicit advisory banner in the generated answer.
3. **Comprehensive Regression Suite & Testing Report:**
   * Full test suite across all 8 modules (Ingestion, Baseline RAG, Hybrid RRF, Guardrails, E2E Integration, Semantic Caching, MCP, and Evaluation API) verified at **72 out of 72 tests passed (100% pass rate)**.
   * Synced [`docs/testing_report.md`](file:///c:/Users/milan/OneDrive/Desktop/Dell_Hackathon_Project/docs/testing_report.md) and [`README.md`](file:///c:/Users/milan/OneDrive/Desktop/Dell_Hackathon_Project/README.md).
