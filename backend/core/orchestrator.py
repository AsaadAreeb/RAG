"""Top-level orchestrator: routes queries and coordinates pipeline execution."""
from __future__ import annotations
from typing import Any

from backend.core.query_router import route_query, QueryType
from backend.pipelines.rag_pipeline import RAGPipeline
from backend.pipelines.sql_pipeline import SQLPipeline
from backend.guardrails.input_guardrails import InputGuardrail
from backend.services.memory_service import MemoryService
from backend.core.config import get_settings

settings = get_settings()


class Orchestrator:
    def __init__(self) -> None:
        self.rag_pipeline = RAGPipeline()
        self.sql_pipeline = SQLPipeline()
        self.input_guard = InputGuardrail()
        self.memory = MemoryService()

    async def handle_query(
        self,
        query: str,
        session_id: str,
        require_sql_approval: bool = True,
    ) -> dict[str, Any]:
        # 1. Input guardrails
        guard_result = self.input_guard.check(query)
        if not guard_result.is_safe:
            return {
                "answer": "Your query was flagged by safety filters.",
                "blocked": True,
                "reason": guard_result.reason,
            }

        # 2. Load conversation memory
        history = await self.memory.get_history(session_id)

        # 3. Route
        decision = route_query(query)

        # 4. Dispatch
        if decision.query_type == QueryType.SQL:
            result = await self.sql_pipeline.run(
                query=query,
                history=history,
                require_approval=require_sql_approval,
                session_id=session_id,
            )
        elif decision.query_type == QueryType.PDF:
            result = await self.rag_pipeline.run(
                query=query,
                history=history,
                session_id=session_id,
            )
        else:  # MIXED — attempt PDF first, surface SQL option
            result = await self.rag_pipeline.run(
                query=query,
                history=history,
                session_id=session_id,
            )
            result["mixed_hint"] = (
                "This query may also benefit from a database lookup. "
                "Ask a SQL-specific question to query the database."
            )

        # 5. Persist to memory
        await self.memory.add_turn(
            session_id=session_id,
            user_msg=query,
            assistant_msg=result.get("answer", ""),
        )

        result["route"] = decision.query_type.value
        result["route_confidence"] = decision.confidence
        return result
