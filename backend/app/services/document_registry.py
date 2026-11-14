from __future__ import annotations

import threading
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone


class DocumentRegistry:
    """Thread-safe registry for indexed documents and their chunk mappings."""
    _instance: Optional[DocumentRegistry] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        # doc_id -> metadata dictionary
        self._documents: Dict[str, Dict[str, Any]] = {}
        # filename -> doc_id (to prevent duplicates)
        self._filename_map: Dict[str, str] = {}
        # state version counter
        self._version_counter: int = 1

    @classmethod
    def get_instance(cls) -> DocumentRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_state_fingerprint(self) -> str:
        """
        Returns a deterministic hash representing the exact state and version
        of all indexed documents in the knowledge base.
        Any addition, modification, or deletion alters this fingerprint immediately.
        """
        with self._lock:
            if not self._documents:
                return "empty"
            # Sort items by document_id to guarantee deterministic hashing
            items = []
            for doc_id, meta in sorted(self._documents.items(), key=lambda x: x[0]):
                items.append(
                    f"{doc_id}:{meta.get('document_version', '1.0')}:{meta.get('upload_timestamp', '')}:{meta.get('chunks_count', 0)}"
                )
            state_raw = "|".join(items) + f"|v{self._version_counter}"
            return hashlib.sha256(state_raw.encode("utf-8")).hexdigest()[:16]

    def has_document(self, filename: str) -> bool:
        with self._lock:
            return filename.lower() in self._filename_map

    def get_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            doc_id = self._filename_map.get(filename.lower())
            return self._documents.get(doc_id) if doc_id else None

    def register(
        self,
        document_id: str,
        document_name: str,
        chunks_count: int,
        pages_count: int,
        file_size_bytes: int,
        document_version: str = "1.0",
        effective_academic_year: Optional[str] = None
    ) -> Dict[str, Any]:
        with self._lock:
            # Determine validity status
            v_lower = (document_version or "1.0").lower().strip()
            if any(ind in v_lower for ind in ["superseded", "replaced", "archived", "old"]):
                validity = "superseded"
            elif any(ind in v_lower for ind in ["expired", "obsolete", "void", "draft"]):
                validity = "expired"
            elif any(ind in v_lower for ind in ["2025", "2026", "current", "active", "latest"]):
                validity = "current"
            elif v_lower in ("1.0", "unknown", ""):
                validity = "unknown"
            else:
                validity = "current"

            ay = effective_academic_year or ("AY 2025-26" if validity == "current" else "AY Unknown")

            meta = {
                "document_id": document_id,
                "document_name": document_name,
                "chunks_count": chunks_count,
                "pages_count": pages_count,
                "file_size_bytes": file_size_bytes,
                "document_version": document_version,
                "validity_status": validity,
                "effective_academic_year": ay,
                "upload_timestamp": datetime.now(timezone.utc).isoformat()
            }
            self._documents[document_id] = meta
            self._filename_map[document_name.lower()] = document_id
            self._version_counter += 1
            return meta

    def list_documents(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._documents.values())

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._documents.get(document_id)

    def delete_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if document_id in self._documents:
                doc = self._documents.pop(document_id)
                self._filename_map.pop(doc["document_name"].lower(), None)
                self._version_counter += 1
                return doc
            return None

