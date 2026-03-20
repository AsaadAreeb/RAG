"""Full RAG pipeline: hybrid retrieval → rerank → LLM → output guard."""
from __future__ import annotations
from typing import Any

from backend.services.embedding_service import EmbeddingService
from backend.services.reranker_service import RerankerService
from backend.services.llm_service import LLMService
from backend.guardrails.output_guardrails import OutputGuardrail
from vectorstore.chroma_store import ChromaStore
from backend.core.config import get_settings

settings = get_settings()

_PROMPT_TEMPLATE = """Using ONLY the context below, answer the question.
If the answer is not present, say "I could not find this in the documents."

Context:
{context}

Question: {question}
Answer:"""


class RAGPipeline:
    def __init__(self) -> None:
        self.embedder = EmbeddingService()
        self.store = ChromaStore()
        self.reranker = RerankerService()
        self.llm = LLMService()
        self.output_guard = OutputGuardrail()

    async def run(
        self,
        query: str,
        history: list[dict],
        session_id: str,
    ) -> dict[str, Any]:
        # 1. Embed query
        q_emb = self.embedder.embed(query)

        # 2. Hybrid retrieval (dense + BM25)
        candidates = self.store.hybrid_search(
            query=query,
            query_embedding=q_emb,
            n_results=settings.top_k + settings.next_k,
            dense_weight=settings.dense_weight,
            bm25_weight=settings.bm25_weight,
        )

        if not candidates:
            return {
                "answer": "No relevant information found in the documents.",
                "evidence": [],
                "additional_matches": [],
                "confidence": 0.0,
                "provider": "none",
            }

        # 3. Rerank all candidates
        ranked = self.reranker.rerank(
            query=query,
            chunks=[{"text": c["text"], "metadata": c["metadata"]} for c in candidates],
        )

        top_chunks = ranked[: settings.top_k]
        next_chunks = ranked[settings.top_k: settings.top_k + settings.next_k]

        # 4. Build context
        context = "\n\n---\n\n".join(c.text for c in top_chunks)

        # 5. Build messages (inject history)
        messages: list[dict] = []
        for h in history[-6:]:  # last 3 pairs
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({
            "role": "user",
            "content": _PROMPT_TEMPLATE.format(context=context, question=query),
        })

        # 6. Generate
        answer, provider = await self.llm.complete(messages, mode="rag")

        # 7. Output guard
        validation = self.output_guard.validate(
            answer=answer,
            context_chunks=[c.text for c in top_chunks],
            retrieval_scores=[c.score for c in top_chunks],
        )

        # 8. Build evidence payload
        evidence = [
            {
                "text": c.text[:500],
                "source": c.metadata.get("filename", "unknown"),
                "chunk_index": c.metadata.get("chunk_index"),
                "score": round(c.score, 4),
                "rank": i + 1,
            }
            for i, c in enumerate(top_chunks)
        ]
        additional = [
            {
                "text": c.text[:300],
                "source": c.metadata.get("filename", "unknown"),
                "chunk_index": c.metadata.get("chunk_index"),
                "score": round(c.score, 4),
                "rank": settings.top_k + i + 1,
            }
            for i, c in enumerate(next_chunks)
        ]

        return {
            "answer": answer,
            "evidence": evidence,
            "additional_matches": additional,
            "confidence": validation.confidence,
            "is_grounded": validation.is_grounded,
            "warnings": validation.warnings,
            "provider": provider,
        }
