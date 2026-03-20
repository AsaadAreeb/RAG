"""LLM layer: Grok (primary) → Gemini (fallback).

Modes
-----
rag         Answer ONLY from retrieved document context
sql         Generate SELECT SQL inside <SQL> tags
naturalize  Convert raw SQL results → natural language (sentence OR markdown table)
"""
from __future__ import annotations
import logging
from typing import AsyncIterator

from openai import AsyncOpenAI, RateLimitError as OpenAIRateLimit
from google import genai
from google.genai import types as gtypes

from backend.core.config import get_settings
from backend.services.rate_limiter import RateLimiter

log = logging.getLogger(__name__)
settings = get_settings()

_SYSTEM: dict[str, str] = {
    "rag": (
        "You are a precise document assistant. "
        "Answer ONLY using the context provided. "
        "If the answer is not in the context say: "
        "\"I could not find this in the documents.\" "
        "Never guess or use outside knowledge. Be concise and factual."
    ),
    "sql": (
        "You are a SQL expert. Generate ONLY a SELECT query inside "
        "<SQL> ... </SQL> tags. "
        "No explanations outside the tags. "
        "No destructive operations (DROP/DELETE/UPDATE/INSERT/ALTER)."
    ),
    "naturalize": (
        "You convert database query results into the most appropriate response format.\n\n"
        "RULES:\n"
        "1. SINGLE VALUE (count, sum, average — 1 row, 1 column):\n"
        "   → Answer in 1-2 natural sentences. Example: \"There are 275 artists.\"\n\n"
        "2. SHORT LIST (2-7 rows):\n"
        "   → Write 1 brief intro sentence, then a clean markdown table.\n\n"
        "3. LONG LIST (8+ rows):\n"
        "   → Write 1 brief intro sentence, then a markdown table.\n"
        "   → If too many rows, show the most relevant ones and note the total.\n\n"
        "4. COMPARISON / RANKING:\n"
        "   → Always use a markdown table.\n\n"
        "ALWAYS:\n"
        "- Use actual names and numbers from the data.\n"
        "- Never mention SQL, table names, column names, or databases.\n"
        "- Markdown table format: | Header | Header |\n"
        "                         |--------|--------|\n"
        "                         | value  | value  |\n"
    ),
}


class LLMService:
    def __init__(self) -> None:
        self._grok = AsyncOpenAI(
            api_key=settings.xai_api_key,
            base_url="https://api.x.ai/v1",
        )
        self._gemini = genai.Client(api_key=settings.gemini_api_key)
        self._limiter = RateLimiter(
            user_rpm=settings.requests_per_user_per_min,
            provider_rpm=settings.rate_limit_rpm,
        )

    async def _grok_complete(
        self, messages: list[dict], system: str,
        temperature: float, max_tokens: int,
    ) -> str:
        full = [{"role": "system", "content": system}] + messages
        resp = await self._grok.chat.completions.create(
            model=settings.grok_model,
            messages=full,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def _grok_stream(
        self, messages: list[dict], system: str,
        temperature: float, max_tokens: int,
    ) -> AsyncIterator[str]:
        full = [{"role": "system", "content": system}] + messages
        stream = await self._grok.chat.completions.create(
            model=settings.grok_model,
            messages=full,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def _gemini_complete(
        self, messages: list[dict], system: str,
        temperature: float, max_tokens: int,
    ) -> str:
        contents = [
            gtypes.Content(
                role="user" if m["role"] == "user" else "model",
                parts=[gtypes.Part.from_text(text=m["content"])],
            )
            for m in messages
        ]
        resp = await self._gemini.aio.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=gtypes.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return resp.text or ""

    async def complete(
        self,
        messages: list[dict],
        mode: str = "rag",
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> tuple[str, str]:
        system   = _SYSTEM.get(mode, _SYSTEM["rag"])
        provider = "grok"

        if not await self._limiter.wait_for_provider("grok", max_wait=5.0):
            provider = "gemini"

        try:
            if provider == "grok":
                answer = await self._grok_complete(
                    messages, system, temperature, max_tokens
                )
            else:
                answer = await self._gemini_complete(
                    messages, system, temperature, max_tokens
                )
        except OpenAIRateLimit:
            log.warning("Grok rate-limited → Gemini fallback")
            provider = "gemini"
            answer = await self._gemini_complete(
                messages, system, temperature, max_tokens
            )
        except Exception as exc:
            log.error("Grok error (%s) → Gemini fallback", exc)
            provider = "gemini"
            answer = await self._gemini_complete(
                messages, system, temperature, max_tokens
            )

        return answer, provider

    async def stream(
        self,
        messages: list[dict],
        mode: str = "rag",
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        system = _SYSTEM.get(mode, _SYSTEM["rag"])
        try:
            async for chunk in self._grok_stream(
                messages, system, temperature, max_tokens
            ):
                yield chunk
        except Exception as exc:
            log.error("Grok stream error (%s) → Gemini fallback", exc)
            fallback = await self._gemini_complete(
                messages, system, temperature, max_tokens
            )
            yield fallback
