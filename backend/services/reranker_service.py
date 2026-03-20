"""Cross-encoder reranker – boosts retrieval precision."""
from __future__ import annotations
from dataclasses import dataclass
from sentence_transformers import CrossEncoder
from backend.core.config import get_settings

import math

settings = get_settings()

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))   # maps any float → (0, 1)

@dataclass
class RankedChunk:
    text: str
    metadata: dict
    score: float
    original_rank: int


class RerankerService:
    _instance: "RerankerService | None" = None

    def __new__(cls) -> "RerankerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = CrossEncoder(settings.reranker_model, max_length=512)
        return cls._instance

    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int | None = None,
    ) -> list[RankedChunk]:
        if not chunks:
            return []
        pairs = [(query, c["text"]) for c in chunks]
        scores = self._model.predict(pairs)
        ranked = sorted(
            [
                RankedChunk(
                    text=c["text"],
                    metadata=c.get("metadata", {}),
                    score=_sigmoid(float(s)),
                    original_rank=i,
                )
                for i, (c, s) in enumerate(zip(chunks, scores))
            ],
            key=lambda x: x.score,
            reverse=True,
        )
        return ranked[:top_k] if top_k else ranked
