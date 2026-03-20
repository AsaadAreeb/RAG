"""Classifies incoming queries as pdf | sql | mixed.

Routing logic:
  - Strong SQL signals  → SQL pipeline
  - Strong PDF signals  → RAG pipeline
  - Ambiguous           → PDF (safer default; LLM is grounded in docs)
  - Pure greeting/meta  → PDF (will return graceful "not found")
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum


class QueryType(str, Enum):
    PDF = "pdf"
    SQL = "sql"
    MIXED = "mixed"


# ── SQL patterns ─────────────────────────────────────────────────────────
# Strong signals that the user wants to query structured data
_SQL_STRONG = re.compile(
    r"\b("
    r"how many|count|total|sum|average|avg|maximum|minimum|max|min|"
    r"list all|show all|show me all|give me all|get all|"
    r"top \d+|bottom \d+|first \d+|last \d+|"
    r"highest|lowest|most|least|best|worst|"
    r"rank|ranking|ranked|"
    r"revenue|sales|orders|invoices|transactions|purchases|"
    r"customers|employees|artists|albums|tracks|genres|products|"
    r"by country|by city|by genre|by year|by month|by region|by category|"
    r"who has the most|which .+ has the most|which .+ has the least|"
    r"group by|order by|where|having|join|"
    r"from the database|in the database|query the database|"
    r"database records|table|rows|columns"
    r")\b",
    re.IGNORECASE,
)

# ── PDF patterns ─────────────────────────────────────────────────────────
# Strong signals that the user wants to query document content
_PDF_STRONG = re.compile(
    r"\b("
    r"according to|the document|the pdf|in the report|in the paper|"
    r"the article|the study|the manual|the guide|the file|"
    r"mentions|states|describes|explains|summarize|summary|"
    r"section|page|paragraph|chapter|introduction|conclusion|"
    r"what does .+ say|what is written|based on the|"
    r"experience|skills|qualifications|background|education|"
    r"resume|cv|profile|biography|about .+\?"
    r")\b",
    re.IGNORECASE,
)

# Weak SQL hints — bump score but not decisive alone
_SQL_WEAK = re.compile(
    r"\b(how much|compare|difference|percentage|ratio|"
    r"per year|per month|trend|growth|breakdown)\b",
    re.IGNORECASE,
)


@dataclass
class RoutingDecision:
    query_type: QueryType
    confidence: float
    reasoning: str


def route_query(query: str) -> RoutingDecision:
    sql_strong = len(_SQL_STRONG.findall(query))
    pdf_strong = len(_PDF_STRONG.findall(query))
    sql_weak   = len(_SQL_WEAK.findall(query))

    sql_score = sql_strong * 2 + sql_weak
    pdf_score = pdf_strong * 2

    if sql_score > 0 and pdf_score == 0:
        conf = min(0.55 + sql_score * 0.1, 0.97)
        return RoutingDecision(
            QueryType.SQL, conf,
            f"SQL signals: {sql_strong} strong + {sql_weak} weak"
        )

    if pdf_score > 0 and sql_score == 0:
        conf = min(0.55 + pdf_score * 0.1, 0.97)
        return RoutingDecision(
            QueryType.PDF, conf,
            f"PDF signals: {pdf_strong} strong"
        )

    if sql_score > 0 and pdf_score > 0:
        # Both present — pick the dominant one
        if sql_score > pdf_score:
            return RoutingDecision(
                QueryType.SQL, 0.60,
                f"Mixed signals, SQL dominant (SQL={sql_score}, PDF={pdf_score})"
            )
        return RoutingDecision(
            QueryType.MIXED, 0.50,
            f"Mixed signals, ambiguous (SQL={sql_score}, PDF={pdf_score})"
        )

    # No strong signals → default to PDF RAG
    return RoutingDecision(QueryType.PDF, 0.50, "No strong signals — default to PDF RAG")
