"""SQL pipeline: generate → validate → (human-approve) → execute → naturalize."""
from __future__ import annotations
import json
from typing import Any

from backend.services.llm_service import LLMService
from backend.guardrails.sql_guardrails import SQLGuardrail
from sql.schema_inspector import SchemaInspector
from sql.query_executor import QueryExecutor
from backend.core.config import get_settings

import redis.asyncio as aioredis

settings    = get_settings()
_PENDING    = "sql_pending:"
_TTL        = 300   # seconds before approval expires


class SQLPipeline:
    def __init__(self) -> None:
        self.llm       = LLMService()
        self.guard     = SQLGuardrail()
        self.inspector = SchemaInspector()
        self.executor  = QueryExecutor()
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    # ─────────────────────────────────────────────────────────────────────
    # Smart naturalizer — LLM decides sentence vs markdown table
    # ─────────────────────────────────────────────────────────────────────
    async def _naturalize(
        self,
        original_query: str,
        sql: str,
        result: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Converts raw SQL rows → best-fit natural language response.
        The LLM picks:
          • 1-2 sentences  for counts / single values
          • markdown table for lists, rankings, comparisons
        """
        if result.get("error"):
            return f"The query could not be completed: {result['error']}", "none"

        rows    = result.get("rows", [])
        columns = result.get("columns", [])

        if not rows:
            return "No results were found for your question.", "none"

        # ── Detect result shape and tell the LLM what it's dealing with ──
        total_rows      = len(rows)
        is_single_val   = total_rows == 1 and len(columns) == 1
        is_short_list   = 2 <= total_rows <= 7
        is_long_list    = total_rows >= 8

        if is_single_val:
            shape_hint = (
                "SHAPE: Single value result — use 1-2 natural sentences."
            )
        elif is_short_list:
            shape_hint = (
                f"SHAPE: Short list ({total_rows} rows) — "
                "use 1 intro sentence + markdown table."
            )
        elif is_long_list:
            shape_hint = (
                f"SHAPE: Long list ({total_rows} rows) — "
                "show a markdown table of the most relevant entries, "
                "mention total count in the intro sentence."
            )
        else:
            shape_hint = "SHAPE: Small result — choose the best format."

        # Limit rows sent to avoid token overflow (keep top 25)
        rows_to_show    = rows[:25]
        truncated_note  = (
            f"(showing top 25 of {total_rows})"
            if total_rows > 25 else f"({total_rows} total)"
        )
        rows_json       = json.dumps(rows_to_show, indent=2, default=str)

        messages = [
            {
                "role": "user",
                "content": (
                    f"User question: \"{original_query}\"\n\n"
                    f"Query result columns: {columns}\n"
                    f"Results {truncated_note}:\n{rows_json}\n\n"
                    f"{shape_hint}\n\n"
                    "Write the best response for the user."
                ),
            }
        ]

        answer, provider = await self.llm.complete(
            messages,
            mode="naturalize",
            temperature=0.2,
            max_tokens=600,
        )
        return answer.strip(), provider

    # ─────────────────────────────────────────────────────────────────────
    # Main pipeline
    # ─────────────────────────────────────────────────────────────────────
    async def run(
        self,
        query: str,
        history: list[dict],
        require_approval: bool,
        session_id: str,
    ) -> dict[str, Any]:

        # 1. Schema
        schema = await self.inspector.get_schema_str()

        # 2. Build prompt (include recent history for context)
        messages: list[dict] = [
            {"role": h["role"], "content": h["content"]}
            for h in history[-4:]
        ]
        messages.append({
            "role": "user",
            "content": (
                f"Database schema:\n{schema}\n\n"
                f"User question: {query}\n\n"
                "Return ONLY the SQL inside <SQL> ... </SQL> tags."
            ),
        })

        # 3. Generate SQL — self-correction loop (max 3 attempts)
        sql: str | None = None
        last_error      = ""
        gen_provider    = "none"

        for attempt in range(3):
            if attempt > 0:
                messages.append({
                    "role": "user",
                    "content": (
                        f"The SQL failed validation: {last_error}. "
                        "Please fix it and return inside <SQL> tags."
                    ),
                })

            raw_output, gen_provider = await self.llm.complete(
                messages, mode="sql"
            )
            sql = self.guard.extract(raw_output)

            if not sql:
                last_error = "No SQL found inside <SQL> tags"
                continue

            v = self.guard.validate(sql)
            if v.is_valid:
                break

            last_error = v.reason
            sql = None

        if not sql:
            return {
                "answer": (
                    f"I wasn't able to generate a valid query for that question "
                    f"after 3 attempts. Last error: {last_error}"
                ),
                "sql": None,
                "status": "generation_failed",
            }

        # 4. Human-in-the-loop gate
        if require_approval:
            r          = await self._get_redis()
            pending_id = f"{session_id}_{abs(hash(sql))}"
            await r.setex(
                f"{_PENDING}{pending_id}",
                _TTL,
                json.dumps({"sql": sql, "query": query}),
            )
            return {
                "answer": (
                    "I've generated the SQL query below. "
                    "Review it and click **Approve & Execute** to run it."
                ),
                "sql":        sql,
                "pending_id": pending_id,
                "status":     "pending_approval",
                "provider":   gen_provider,
            }

        # 5. Auto-execute (trusted/admin path)
        result                        = await self.executor.execute(sql)
        natural_answer, nat_provider  = await self._naturalize(
            query, sql, result
        )
        return {
            "answer":   natural_answer,
            "sql":      sql,
            "result":   result,
            "status":   "executed",
            "provider": nat_provider or gen_provider,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Approve & execute  (called from /sql/approve endpoint)
    # ─────────────────────────────────────────────────────────────────────
    async def approve_and_execute(self, pending_id: str) -> dict[str, Any]:
        r   = await self._get_redis()
        raw = await r.get(f"{_PENDING}{pending_id}")

        if not raw:
            return {
                "error":  "Query not found or approval window expired (5 min timeout).",
                "status": "error",
            }

        data           = json.loads(raw)
        sql            = data["sql"]
        original_query = data.get("query", "your question")
        await r.delete(f"{_PENDING}{pending_id}")

        # Execute
        result = await self.executor.execute(sql)

        # Convert to natural language
        natural_answer, provider = await self._naturalize(
            original_query, sql, result
        )
        return {
            "answer":   natural_answer,
            "sql":      sql,
            "result":   result,
            "status":   "executed",
            "provider": provider,
        }
