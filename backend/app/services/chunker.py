from __future__ import annotations

import re
from typing import List, Dict, Any


def is_heading(line: str) -> bool:
    """Detect if a line looks like a policy section heading."""
    line_clean = line.strip()
    if not line_clean:
        return False
    
    # Matches patterns like:
    # "SECTION 1. ACADEMIC INTEGRITY"
    # "1.0 ATTENDANCE REQUIREMENTS"
    # "Article IV - Violations"
    # "Policy Overview:"
    # Short lines entirely uppercase (e.g., "DISCIPLINARY PROCEDURES")
    patterns = [
        r'^(section|article|policy|chapter|rule|clause|part)\s+[\w\d\.\-]+.*',
        r'^\d+(\.\d+)*\s+[A-Z].*',
        r'^[A-Z0-9\s\-_:]{4,60}$'
    ]
    
    for pat in patterns:
        if re.match(pat, line_clean, re.IGNORECASE) and len(line_clean) < 100:
            return True
            
    return False


def chunk_extracted_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = 1000,
    chunk_overlap: int = 150
) -> List[Dict[str, Any]]:
    """
    Performs section-aware chunking over extracted PDF pages.
    Preserves heading context and groups clauses logically.
    
    Input pages format: [{"page_number": int, "text": str}]
    Returns list of dicts: [{"text": str, "page_number": int, "section_heading": str}]
    """
    chunks: List[Dict[str, Any]] = []
    current_heading = "General Policy Provisions"
    
    for page_data in pages:
        page_num = page_data["page_number"]
        page_text = page_data["text"]
        
        # Split page into lines/paragraphs
        lines = [line.strip() for line in page_text.split("\n") if line.strip()]
        
        current_block: List[str] = []
        current_len = 0
        
        for line in lines:
            if is_heading(line):
                # When encountering a new section heading, finalize current block if it holds text
                if current_block:
                    full_text = " ".join(current_block)
                    chunks.append({
                        "text": full_text,
                        "page_number": page_num,
                        "section_heading": current_heading
                    })
                    current_block = []
                    current_len = 0
                current_heading = line
                continue
            
            # Add line to current block
            current_block.append(line)
            current_len += len(line) + 1
            
            # If block reaches target chunk size, commit chunk and keep overlap
            if current_len >= chunk_size:
                full_text = " ".join(current_block)
                chunks.append({
                    "text": full_text,
                    "page_number": page_num,
                    "section_heading": current_heading
                })
                
                # Keep last part for overlap
                overlap_tokens: List[str] = []
                overlap_len = 0
                for token in reversed(current_block):
                    overlap_tokens.insert(0, token)
                    overlap_len += len(token) + 1
                    if overlap_len >= chunk_overlap:
                        break
                
                current_block = overlap_tokens
                current_len = overlap_len
        
        # Flush any remaining text on the page
        if current_block:
            full_text = " ".join(current_block)
            chunks.append({
                "text": full_text,
                "page_number": page_num,
                "section_heading": current_heading
            })
            
    return chunks

