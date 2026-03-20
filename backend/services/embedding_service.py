"""Local sentence-transformer embeddings with caching."""
from __future__ import annotations
import hashlib
from functools import lru_cache
from typing import Sequence
from sentence_transformers import SentenceTransformer

from backend.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    _instance: "EmbeddingService | None" = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = SentenceTransformer(settings.embedding_model)
            cls._instance._cache: dict[str, list[float]] = {}
        return cls._instance

    def embed(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode()).hexdigest()
        if key not in self._cache:
            vec = self._model.encode(text, normalize_embeddings=True)
            self._cache[key] = vec.tolist()
        return self._cache[key]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        uncached = [(i, t) for i, t in enumerate(texts)
                    if hashlib.sha256(t.encode()).hexdigest() not in self._cache]
        if uncached:
            indices, raw = zip(*uncached)
            vecs = self._model.encode(list(raw), normalize_embeddings=True,
                                      batch_size=32, show_progress_bar=False)
            for idx, vec in zip(indices, vecs):
                key = hashlib.sha256(raw[list(indices).index(idx)].encode()).hexdigest()
                self._cache[key] = vec.tolist()
        return [self.embed(t) for t in texts]
