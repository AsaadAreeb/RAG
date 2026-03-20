"""ChromaDB persistent store with BM25 hybrid retrieval."""
from __future__ import annotations
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

from backend.core.config import get_settings

settings = get_settings()


class ChromaStore:
    _instance: "ChromaStore | None" = None

    def __new__(cls) -> "ChromaStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = chromadb.PersistentClient(
                path=settings.chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            cls._instance._col = cls._instance._client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
        return cls._instance

    # ── Indexing ──────────────────────────────────────────────────────────────
    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        self._col.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def get_existing_hashes(self, doc_id: str) -> set[str]:
        results = self._col.get(
            where={"doc_id": {"$eq": doc_id}},
            include=["metadatas"],
        )
        hashes = set()
        for meta in results.get("metadatas") or []:
            if meta and "content_hash" in meta:
                hashes.add(meta["content_hash"])
        return hashes

    def delete_document(self, doc_id: str) -> None:
        results = self._col.get(where={"doc_id": {"$eq": doc_id}}, include=[])
        ids = results.get("ids") or []
        if ids:
            self._col.delete(ids=ids)

    # ── Dense retrieval ───────────────────────────────────────────────────────
    def dense_search(
        self,
        query_embedding: list[float],
        n_results: int = 20,
    ) -> list[dict[str, Any]]:
        results = self._col.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self._col.count() or 1),
            include=["documents", "metadatas", "distances"],
        )
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        dists = results["distances"][0] if results["distances"] else []
        return [
            {"text": d, "metadata": m, "distance": dist, "score": 1 - dist}
            for d, m, dist in zip(docs, metas, dists)
        ]

    # ── BM25 retrieval ────────────────────────────────────────────────────────
    def bm25_search(self, query: str, n_results: int = 20) -> list[dict[str, Any]]:
        all_data = self._col.get(include=["documents", "metadatas"])
        docs = all_data.get("documents") or []
        metas = all_data.get("metadatas") or []
        if not docs:
            return []
        tokenized = [d.lower().split() for d in docs]
        bm25 = BM25Okapi(tokenized)
        # scores = bm25.get_scores(query.lower().split())
        raw_scores = bm25.get_scores(query.lower().split())
        # ── Normalize BM25 to [0, 1] ──────────────────────────────
        max_s = max(raw_scores) if max(raw_scores) > 0 else 1.0
        scores = raw_scores / max_s          # numpy divide, now all in [0,1]
        
        ranked = sorted(
            zip(scores, docs, metas), key=lambda x: x[0], reverse=True
        )[:n_results]
        return [
            {"text": d, "metadata": m, "score": float(s), "distance": 1 - float(s)}
            for s, d, m in ranked
        ]

    # ── Hybrid retrieval ──────────────────────────────────────────────────────
    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        n_results: int = 20,
        dense_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ) -> list[dict[str, Any]]:
        dense = self.dense_search(query_embedding, n_results)
        bm25 = self.bm25_search(query, n_results)

        # Merge by text key, combine scores
        merged: dict[str, dict] = {}
        for item in dense:
            key = item["text"]
            merged[key] = {**item, "hybrid_score": item["score"] * dense_weight}
        for item in bm25:
            key = item["text"]
            if key in merged:
                merged[key]["hybrid_score"] += item["score"] * bm25_weight
            else:
                merged[key] = {**item, "hybrid_score": item["score"] * bm25_weight}

        return sorted(merged.values(), key=lambda x: x["hybrid_score"], reverse=True)

    def count(self) -> int:
        return self._col.count()
