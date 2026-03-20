"""Safe async SQL executor — SELECT-only, schema-validated."""
from __future__ import annotations
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.core.config import get_settings
from backend.guardrails.sql_guardrails import SQLGuardrail

settings = get_settings()
_guard = SQLGuardrail()


class QueryExecutor:
    def __init__(self, database_url: str | None = None) -> None:
        self._url = database_url or settings.database_url

    async def execute(self, sql: str) -> dict[str, Any]:
        validation = _guard.validate(sql)
        if not validation.is_valid:
            return {"error": validation.reason, "rows": [], "columns": []}

        engine = create_async_engine(self._url, echo=False)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text(sql))
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return {"rows": rows, "columns": columns, "error": None}
        except Exception as exc:
            return {"error": str(exc), "rows": [], "columns": []}
        finally:
            await engine.dispose()
