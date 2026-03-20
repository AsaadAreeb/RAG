"""Redis-backed conversation memory with token-aware summarisation."""
from __future__ import annotations
import json
import time
from typing import Any

import redis.asyncio as aioredis

from backend.core.config import get_settings

settings = get_settings()

MAX_TURNS = 10
TTL_SECONDS = 3600  # 1 hour


class MemoryService:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _key(self, session_id: str) -> str:
        return f"memory:{session_id}"

    async def get_history(self, session_id: str) -> list[dict[str, str]]:
        r = await self._get_redis()
        raw = await r.get(self._key(session_id))
        if not raw:
            return []
        return json.loads(raw)

    async def add_turn(
        self, session_id: str, user_msg: str, assistant_msg: str
    ) -> None:
        r = await self._get_redis()
        history = await self.get_history(session_id)
        history.append({"role": "user", "content": user_msg, "ts": str(time.time())})
        history.append({"role": "assistant", "content": assistant_msg,
                        "ts": str(time.time())})
        # Keep only the last MAX_TURNS pairs
        if len(history) > MAX_TURNS * 2:
            history = history[-(MAX_TURNS * 2):]
        await r.setex(self._key(session_id), TTL_SECONDS, json.dumps(history))

    async def clear(self, session_id: str) -> None:
        r = await self._get_redis()
        await r.delete(self._key(session_id))

    async def get_formatted(self, session_id: str) -> list[dict[str, str]]:
        history = await self.get_history(session_id)
        return [{"role": h["role"], "content": h["content"]} for h in history]
