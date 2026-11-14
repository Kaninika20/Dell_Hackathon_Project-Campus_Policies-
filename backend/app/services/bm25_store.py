from __future__ import annotations

"""BM25 store — singleton that holds the keyword index across all ingested chunks."""

import threading
from typing import List, Dict, Any, Optional

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


class BM25Store:
    _instance: Optional["BM25Store"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._chunks: List[Dict[str, Any]] = []
        self._bm25: Optional[BM25Okapi] = None

    @classmethod
    def get_instance(cls) -> "BM25Store":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Add chunks and rebuild the BM25 index."""
        with self._lock:
            self._chunks.extend(chunks)
            tokenized = [_tokenize(c["text"]) for c in self._chunks]
            self._bm25 = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Return top-k chunks by BM25 score."""
        with self._lock:
            if not self._bm25 or not self._chunks:
                return []
            scores = self._bm25.get_scores(_tokenize(query))
            ranked = sorted(
                enumerate(scores), key=lambda x: x[1], reverse=True
            )[:top_k]
            results = []
            for idx, score in ranked:
                if score > 0:
                    chunk = dict(self._chunks[idx])
                    chunk["bm25_score"] = float(score)
                    results.append(chunk)
            return results

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

