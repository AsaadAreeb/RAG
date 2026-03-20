"""RAG output guardrails: grounding check + confidence scoring."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class OutputValidation:
    is_grounded: bool
    confidence: float
    warnings: list[str]


def _overlap_ratio(answer: str, context: str) -> float:
    a_words = set(answer.lower().split())
    c_words = set(context.lower().split())
    if not a_words:
        return 0.0
    return len(a_words & c_words) / len(a_words)


class OutputGuardrail:
    def validate(
        self,
        answer: str,
        context_chunks: list[str],
        retrieval_scores: list[float],
    ) -> OutputValidation:
        warnings: list[str] = []

        if not context_chunks:
            return OutputValidation(False, 0.0, ["No context retrieved"])

        # Grounding: how much of the answer overlaps with retrieved context
        combined_context = " ".join(context_chunks)
        overlap = _overlap_ratio(answer, combined_context)

        # Uncertainty phrases → lower confidence
        hedges = ["i don't know", "i'm not sure", "cannot determine",
                  "not found", "no information", "could not find"]
        has_hedge = any(h in answer.lower() for h in hedges)

        # Avg retrieval score
        avg_score = sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0.0

        confidence = round(
            0.4 * min(overlap * 2, 1.0) +
            0.4 * max(0.0, min(avg_score, 1.0)) +
            0.2 * (0.3 if has_hedge else 1.0),
            3
        )

        is_grounded = overlap > 0.05 or has_hedge

        if overlap < 0.05 and not has_hedge:
            warnings.append("Answer may not be grounded in retrieved context")
        if avg_score < 0.3:
            warnings.append("Low retrieval confidence")

        return OutputValidation(is_grounded, confidence, warnings)
