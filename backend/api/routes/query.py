from __future__ import annotations
import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.core.orchestrator import Orchestrator
from backend.core.config import get_settings
from backend.services.rate_limiter import RateLimiter

router = APIRouter()
settings = get_settings()
_orch = Orchestrator()
_limiter = RateLimiter(user_rpm=settings.requests_per_user_per_min)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    session_id: str = Field(default="default")
    stream: bool = False
    require_sql_approval: bool = True


@router.post("/query")
async def query(req: QueryRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _limiter.check_user(client_ip):
        raise HTTPException(429, "Rate limit exceeded. Try again in a minute.")

    if req.stream:
        return StreamingResponse(
            _stream_query(req), media_type="text/event-stream"
        )

    return await _orch.handle_query(
        query=req.query,
        session_id=req.session_id,
        require_sql_approval=req.require_sql_approval,
    )


async def _stream_query(req: QueryRequest) -> AsyncIterator[str]:
    from backend.guardrails.input_guardrails import InputGuardrail
    guard = InputGuardrail()
    check = guard.check(req.query)
    if not check.is_safe:
        yield f"data: {json.dumps(dict(error=check.reason, done=True))}\\n\\n"
        return

    from backend.services.llm_service import LLMService
    from backend.services.memory_service import MemoryService
    from backend.services.embedding_service import EmbeddingService
    from vectorstore.chroma_store import ChromaStore
    from backend.services.reranker_service import RerankerService

    mem = MemoryService()
    history = await mem.get_history(req.session_id)
    embedder = EmbeddingService()
    store = ChromaStore()
    reranker = RerankerService()
    llm = LLMService()

    q_emb = embedder.embed(req.query)
    candidates = store.hybrid_search(req.query, q_emb, n_results=20)
    if not candidates:
        yield f"data: {json.dumps(dict(chunk='No relevant information found.', done=True))}\\n\\n"
        return

    ranked = reranker.rerank(
        req.query,
        [{"text": c["text"], "metadata": c["metadata"]} for c in candidates],
        top_k=settings.top_k,
    )
    context = "\\n\\n---\\n\\n".join(c.text for c in ranked)
    messages = [{"role": h["role"], "content": h["content"]} for h in history[-6:]]
    messages.append({
        "role": "user",
        "content": (
            "Using ONLY the context below, answer the question.\\n\\n"
            f"Context:\\n{context}\\n\\nQuestion: {req.query}\\nAnswer:"
        ),
    })

    full_answer = ""
    async for chunk in llm.stream(messages, mode="rag"):
        full_answer += chunk
        yield f"data: {json.dumps(dict(chunk=chunk, done=False))}\\n\\n"

    evidence = [
        {
            "text": c.text[:400],
            "source": c.metadata.get("filename", "unknown"),
            "score": round(c.score, 4),
            "rank": i + 1,
        }
        for i, c in enumerate(ranked)
    ]
    yield f"data: {json.dumps(dict(chunk='', evidence=evidence, done=True))}\\n\\n"
    await mem.add_turn(req.session_id, req.query, full_answer)