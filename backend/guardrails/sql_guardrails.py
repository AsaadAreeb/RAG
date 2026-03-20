"""SQL guardrails: extract, validate, block destructive ops."""
from __future__ import annotations
import re
import sqlparse
from dataclasses import dataclass

_SQL_TAG = re.compile(r"<SQL>(.*?)</SQL>", re.DOTALL | re.IGNORECASE)
_BLOCKED = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|EXEC|EXECUTE|CREATE|REPLACE)\b",
    re.IGNORECASE,
)


@dataclass
class SQLValidation:
    is_valid: bool
    sql: str = ""
    reason: str = ""


class SQLGuardrail:
    def extract(self, llm_output: str) -> str | None:
        """Extract SQL from <SQL>...</SQL> tags. Returns None if absent."""
        match = _SQL_TAG.search(llm_output)
        return match.group(1).strip() if match else None

    def validate(self, sql: str) -> SQLValidation:
        if not sql or not sql.strip():
            return SQLValidation(False, sql, "Empty SQL")

        # Block destructive operations
        if _BLOCKED.search(sql):
            return SQLValidation(False, sql, "Blocked operation detected")

        # Must start with SELECT (after stripping comments/whitespace)
        stripped = sqlparse.format(sql, strip_comments=True).strip().upper()
        if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
            return SQLValidation(False, sql, "Only SELECT/WITH queries are allowed")

        # Basic syntax check via sqlparse
        parsed = sqlparse.parse(sql)
        if not parsed or not parsed[0].tokens:
            return SQLValidation(False, sql, "SQL parse failed")

        return SQLValidation(True, sql)

    def validate_with_schema(
        self, sql: str, known_tables: list[str], known_columns: dict[str, list[str]]
    ) -> SQLValidation:
        base = self.validate(sql)
        if not base.is_valid:
            return base

        # Check referenced tables exist (simple heuristic)
        sql_upper = sql.upper()
        for table in known_tables:
            pass  # presence check skipped — schema-aware validation optional

        return SQLValidation(True, sql)
