"""
mcp_server.py — Model Context Protocol (MCP) Server for CampusPolicy AI

Exposes official university policy discovery and document inspection capabilities
as standardized MCP tools:
  1. search_policy: Multi-mode hybrid semantic search over official handbooks.
  2. get_policy_document: Retrieve all clauses & structure of a specific handbook.
  3. list_available_policies: Discover all currently indexed policy handbooks.

Run standalone via standard stdio:
  python -m app.mcp_server
"""
from __future__ import annotations

import sys
import json
import asyncio
from typing import Dict, Any, List, Optional

from mcp.server.mcpserver import MCPServer
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.core.qdrant_client import get_qdrant_client
from app.services.document_registry import DocumentRegistry
from app.services.hybrid_retrieval import multi_mode_retrieve
from app.services.guardrails import sanitise_user_query, build_version_warning

# Initialize the Model Context Protocol Server
mcp = MCPServer(
    name="campuspolicy-ai",
    version="1.0.0",
    instructions=(
        "You are connected to CampusPolicy AI, the official university policy discovery service. "
        "Use these tools to discover, retrieve, and inspect authentic university regulations, student codes, "
        "and examination policies. Never invent policy numbers or exceptions; always reference retrieved evidence."
    )
)


# ---------------------------------------------------------------------------
# Tool 1: search_policy
# ---------------------------------------------------------------------------

@mcp.tool(
    name="search_policy",
    description=(
        "Searches official university policy documents using semantic and keyword retrieval. "
        "Returns genuine policy clauses, document names, page numbers, and section headings. "
        "Supports 'baseline' (direct vector), 'hyde' (query expansion), and 'hyde_hybrid' (dense + BM25 fusion)."
    )
)
async def search_policy(
    query: str,
    retrieval_method: str = "hyde_hybrid",
    top_k: int = 5
) -> str:
    """
    Executes hybrid retrieval over authentic campus policy documents.
    """
    clean_query = query.strip()
    if not clean_query:
        return json.dumps({"error": "Query cannot be empty.", "results": []})

    # Guardrails: Sanitise user query for prompt injection
    sanitised_query, injection_detected = sanitise_user_query(clean_query)

    norm_method = retrieval_method.lower().strip()
    if norm_method not in ("baseline", "hyde", "hyde_hybrid", "hybrid"):
        norm_method = "hyde_hybrid"

    try:
        # Retrieve actual policy chunks
        chunks, meta = multi_mode_retrieve(
            query=sanitised_query,
            method=norm_method,
            top_k=top_k
        )

        version_warning = build_version_warning(chunks)

        results = []
        for rank, c in enumerate(chunks, start=1):
            results.append({
                "rank": rank,
                "document_name": c.get("document_name", "Unknown"),
                "page_number": c.get("page_number", 1),
                "section_heading": c.get("section_heading", "Policy Clause"),
                "text": c.get("text", "").strip(),
                "document_version": c.get("document_version", "1.0"),
            })

        output = {
            "query": sanitised_query,
            "retrieval_method": meta.get("retrieval_method"),
            "results_count": len(results),
            "policy_evidence": results,
            "version_warning": version_warning if version_warning else None,
            "query_injection_detected": injection_detected,
            "telemetry": {
                "latency_ms": meta.get("latency_ms"),
                "chunks_retrieved": meta.get("chunks_retrieved"),
            }
        }
        return json.dumps(output, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Policy search failed: {str(e)}",
            "results": []
        })


# ---------------------------------------------------------------------------
# Tool 2: get_policy_document
# ---------------------------------------------------------------------------

@mcp.tool(
    name="get_policy_document",
    description=(
        "Retrieves the complete metadata and all indexed policy clauses for a specific "
        "university handbook by its document ID or filename (e.g. 'SAMPLE_Academic_Integrity_Policy.pdf')."
    )
)
async def get_policy_document(document_id_or_name: str) -> str:
    """
    Inspects full handbook clauses from Qdrant and DocumentRegistry.
    """
    identifier = document_id_or_name.strip()
    if not identifier:
        return json.dumps({"error": "document_id_or_name parameter is required."})

    reg = DocumentRegistry.get_instance()

    # Check by ID or by filename
    doc_info = reg.get_document(identifier) or reg.get_by_filename(identifier)

    if not doc_info:
        available = [d["document_name"] for d in reg.list_documents()]
        return json.dumps({
            "error": f"Policy document '{identifier}' not found in registry.",
            "available_documents": available
        }, indent=2)

    doc_id = doc_info["document_id"]

    # Fetch all chunks from Qdrant for this document
    clauses: List[Dict[str, Any]] = []
    try:
        client = get_qdrant_client()
        hits, _ = client.scroll(
            collection_name=settings.qdrant_collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            ),
            limit=100,
            with_payload=True
        )

        # Sort clauses by page number
        sorted_hits = sorted(hits, key=lambda h: (h.payload or {}).get("page_number", 0))

        for h in sorted_hits:
            p = h.payload or {}
            clauses.append({
                "page_number": p.get("page_number", 1),
                "section_heading": p.get("section_heading", "Clause"),
                "text": p.get("text", "")
            })
    except Exception as e:
        clauses = [{"error": f"Failed to scroll Qdrant chunks: {str(e)}"}]

    output = {
        "document_id": doc_info["document_id"],
        "document_name": doc_info["document_name"],
        "document_version": doc_info.get("document_version", "1.0"),
        "pages_count": doc_info.get("pages_count", 1),
        "total_clauses": len(clauses),
        "upload_timestamp": doc_info.get("upload_timestamp"),
        "clauses": clauses
    }
    return json.dumps(output, indent=2)


# ---------------------------------------------------------------------------
# Tool 3: list_available_policies
# ---------------------------------------------------------------------------

@mcp.tool(
    name="list_available_policies",
    description=(
        "Lists all official university policy handbooks currently indexed and available "
        "in the knowledge base, along with page counts, clause counts, and version numbers."
    )
)
async def list_available_policies() -> str:
    """
    Returns an inventory of indexed policy documents.
    """
    reg = DocumentRegistry.get_instance()
    docs = reg.list_documents()

    output = {
        "total_policies_indexed": len(docs),
        "policies": [
            {
                "document_id": d["document_id"],
                "document_name": d["document_name"],
                "document_version": d.get("document_version", "1.0"),
                "pages_count": d.get("pages_count", 0),
                "clauses_count": d.get("chunks_count", 0),
                "upload_timestamp": d.get("upload_timestamp"),
            }
            for d in docs
        ]
    }
    return json.dumps(output, indent=2)


# ---------------------------------------------------------------------------
# Direct Dispatcher (for programmatic / unit test invocation)
# ---------------------------------------------------------------------------

async def dispatch_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Programmatic entry point for calling registered MCP tools directly.
    """
    if tool_name == "search_policy":
        return await search_policy(
            query=arguments.get("query", ""),
            retrieval_method=arguments.get("retrieval_method", "hyde_hybrid"),
            top_k=arguments.get("top_k", 5)
        )
    elif tool_name == "get_policy_document":
        return await get_policy_document(
            document_id_or_name=arguments.get("document_id_or_name", "")
        )
    elif tool_name == "list_available_policies":
        return await list_available_policies()
    else:
        raise ValueError(f"Unknown MCP tool: '{tool_name}'")


# ---------------------------------------------------------------------------
# Main entrypoint for stdio transport
# ---------------------------------------------------------------------------

def run_server():
    """Runs the MCP server over standard input/output (stdio)."""
    mcp.run()


if __name__ == "__main__":
    run_server()

