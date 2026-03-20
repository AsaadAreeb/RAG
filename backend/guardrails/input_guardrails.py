"""Input safety: detect prompt injection, system overrides, malicious patterns."""
from __future__ import annotations
import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    re.compile(r"ignore (all |previous |above |your )?instructions?", re.I),
    re.compile(r"system\s*prompt", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"disregard (all |your )?", re.I),
    re.compile(r"act as (if you are|a )?", re.I),
    re.compile(r"forget (everything|all|your training)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"DAN\b", re.I),
    re.compile(r"<\s*script", re.I),
    re.compile(r"eval\s*\(", re.I),
]


@dataclass
class GuardResult:
    is_safe: bool
    reason: str = ""


class InputGuardrail:
    def check(self, text: str) -> GuardResult:
        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                return GuardResult(False, f"Blocked pattern: {pattern.pattern}")
        if len(text) > 8_000:
            return GuardResult(False, "Query too long (>8000 chars)")
        return GuardResult(True)
