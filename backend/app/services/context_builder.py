from __future__ import annotations

from typing import List, Dict, Any, Tuple

from app.services.guardrails import sanitise_chunk_text, build_version_warning, detect_policy_conflicts


def build_evidence_context(
    chunks: List[Dict[str, Any]]
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Constructs a structured, sanitised context string for Gemini prompt input.

    Changes from baseline:
    - Each chunk's text is sanitised for prompt injection before entering the context.
    - A version/validity warning is computed from document metadata.
    - Potential policy conflicts across documents are detected.

    Returns:
      (formatted_context_string, validated_evidence_list, guardrail_metadata)

    guardrail_metadata keys:
      - version_warning (str)      : prepend to answer if non-empty
      - chunk_injection_detected (bool): any chunk contained injection patterns
      - policy_conflicts (list)    : list of {shared_heading, documents} dicts
    """
    if not chunks:
        return "", [], {
            "version_warning": "",
            "chunk_injection_detected": False,
            "policy_conflicts": [],
        }

    context_blocks: List[str] = []
    evidence_list: List[Dict[str, Any]] = []
    any_chunk_injection = False

    for idx, c in enumerate(chunks, start=1):
        doc_name = c.get("document_name", "Unknown")
        page = c.get("page_number", 1)
        heading = c.get("section_heading", "Policy Section")
        raw_text = c.get("text", "").strip()

        # --- Prompt injection guard on chunk text ---
        clean_text, injection_in_chunk = sanitise_chunk_text(raw_text)
        if injection_in_chunk:
            any_chunk_injection = True

        block = (
            f"=== EVIDENCE #{idx} ===\n"
            f"Document: {doc_name}\n"
            f"Page: {page}\n"
            f"Section: {heading}\n"
            f"Content:\n{clean_text}\n"
        )
        context_blocks.append(block)

        evidence_list.append({
            "document_name": doc_name,
            "page_number": page,
            "section_heading": heading,
            "excerpt": clean_text[:350] + ("..." if len(clean_text) > 350 else ""),
            "document_version": c.get("document_version", "1.0"),
        })

    formatted_context = "\n----------------------------------------\n".join(context_blocks)

    # --- Version/validity warnings ---
    version_warning = build_version_warning(chunks)

    # --- Conflict detection ---
    conflicts = detect_policy_conflicts(chunks)

    guardrail_meta = {
        "version_warning": version_warning,
        "chunk_injection_detected": any_chunk_injection,
        "policy_conflicts": conflicts,
    }

    return formatted_context, evidence_list, guardrail_meta
