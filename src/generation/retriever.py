"""In-memory embedding index with cosine similarity search.

Data sizes are small (~2.5K misconceptions, ~1.6K questions, 15 PF exercises)
so brute-force cosine similarity via numpy is sufficient.
Embeddings are cached to disk to avoid re-computation.
"""

import pickle
from pathlib import Path
from typing import Any

import numpy as np

from src.utils.llm_client import LLMClient

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "embeddings"


class EmbeddingIndex:
    """In-memory embedding index with cosine similarity search.

    Usage:
        index = EmbeddingIndex(embed_client)
        index.add(items, text_field="name")
        results = index.search("query text", k=5)
    """

    def __init__(self, embed_client: LLMClient):
        self.embed = embed_client
        self.vectors: np.ndarray | None = None
        self.items: list[dict[str, Any]] = []

    # ── Public API ──────────────────────────────────────────────────────────

    def add(
        self,
        items: list[dict[str, Any]],
        text_field: str = "text",
        cache_key: str | None = None,
    ) -> None:
        """Embed and index a list of items.

        Args:
            items: List of dicts, each must have *text_field*.
            text_field: Key whose value will be embedded.
            cache_key: Optional name for disk caching (skips re-embedding
                       if cached vectors already exist).
        """
        # Try loading from cache
        if cache_key is not None:
            cached = self._load_cache(cache_key)
            if cached is not None:
                self.vectors, self.items = cached
                return

        texts = [item[text_field] for item in items]
        raw_vectors = self.embed.embed(texts)
        self.vectors = np.array(raw_vectors, dtype=np.float32)
        self.items = items

        # Save cache
        if cache_key is not None:
            self._save_cache(cache_key)

    def search(
        self,
        query: str,
        k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Return top-k most similar items by cosine similarity.

        Args:
            query: Text to search for.
            k: Number of results.
            min_score: Minimum similarity score threshold.

        Returns:
            List of items with a 'score' key added.
        """
        if self.vectors is None or len(self.items) == 0:
            return []

        q_vec = np.array(self.embed.embed(query), dtype=np.float32).flatten()

        # Cosine similarity via normalized dot product
        norms = np.linalg.norm(self.vectors, axis=1)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0 or np.any(norms == 0):
            return []

        sims = (self.vectors @ q_vec) / (norms * q_norm)

        # Filter by threshold, then get top-k
        valid = np.where(sims >= min_score)[0]
        if len(valid) == 0:
            return []

        top_k = valid[np.argsort(sims[valid])[-k:]][::-1]
        return [{**self.items[i], "score": float(sims[i])} for i in top_k]

    def search_by_vector(
        self,
        vector: list[float],
        k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search using a raw embedding vector instead of a text query."""
        if self.vectors is None or len(self.items) == 0:
            return []

        q_vec = np.array(vector, dtype=np.float32).flatten()
        norms = np.linalg.norm(self.vectors, axis=1)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0 or np.any(norms == 0):
            return []

        sims = (self.vectors @ q_vec) / (norms * q_norm)
        valid = np.where(sims >= min_score)[0]
        if len(valid) == 0:
            return []

        top_k = valid[np.argsort(sims[valid])[-k:]][::-1]
        return [{**self.items[i], "score": float(sims[i])} for i in top_k]

    @property
    def size(self) -> int:
        return len(self.items) if self.vectors is not None else 0

    # ── Cache ───────────────────────────────────────────────────────────────

    def _cache_path(self, key: str) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_DIR / f"{key}.pkl"

    def _load_cache(self, key: str) -> tuple | None:
        path = self._cache_path(key)
        if path.exists():
            with open(path, "rb") as f:
                return pickle.load(f)
        return None

    def _save_cache(self, key: str) -> None:
        path = self._cache_path(key)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump((self.vectors, self.items), f)
