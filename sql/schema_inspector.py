"""Reads the live schema so the LLM generates accurate SQL."""
from __future__ import annotations
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from backend.core.config import get_settings

settings = get_settings()


class SchemaInspector:
    def __init__(self, database_url: str | None = None) -> None:
        self._url = database_url or settings.database_url

    async def get_schema_str(self) -> str:
        engine = create_async_engine(self._url, echo=False)

        def _read_schema(sync_conn):
            """Runs synchronously inside the async greenlet via run_sync."""
            inspector = inspect(sync_conn)
            table_names = inspector.get_table_names()
            parts = []
            for table in table_names:
                cols = inspector.get_columns(table)
                col_defs = ", ".join(
                    f"{c['name']} {str(c['type'])}" for c in cols
                )
                parts.append(f"Table {table}({col_defs})")
            return "\n".join(parts)

        try:
            async with engine.connect() as conn:
                # run_sync bridges async connection → sync inspect call
                schema_str = await conn.run_sync(_read_schema)
            return schema_str
        finally:
            await engine.dispose()
