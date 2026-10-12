"""作品事件流：写入 Redis List（供 SSE 回放/续传），并发布到频道（供实时推送）。

事件结构：{"seq": N, "event": "...", "data": {...}}，seq 从 0 单调递增。
Redis 键：works:{id}:events（List，EXPIRE 30min） / works:{id}:ch（PubSub）
"""
import asyncio
import json

import redis.asyncio as aioredis

from app.core.config import get_settings

_settings = get_settings()
_pool: aioredis.Redis | None = None


def redis_client() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(_settings.redis_url, decode_responses=True)
    return _pool


class WorkEvents:
    def __init__(self, work_id: int):
        self.work_id = work_id
        self.list_key = f"works:{work_id}:events"
        self.chan = f"works:{work_id}:ch"
        self._seq = -1
        self._client = redis_client()

    @classmethod
    async def seq_of(cls, work_id: int) -> int:
        return await redis_client().llen(f"works:{work_id}:events") - 1

    async def emit(self, event: str, data: dict | None = None) -> int:
        """仅 worker 调用（单写者，seq 用 LLEN 推算）。"""
        seq = await self._client.llen(self.list_key)
        payload = json.dumps({"seq": seq, "event": event, "data": data or {}}, ensure_ascii=False)
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.rpush(self.list_key, payload)
            pipe.expire(self.list_key, 1800)
            pipe.publish(self.chan, payload)
            await pipe.execute()
        return seq

    async def poll_new(self, after_seq: int) -> list[dict]:
        """SSE 端轮询：返回 seq > after_seq 的事件。"""
        total = await self._client.llen(self.list_key)
        if total <= after_seq + 1:
            return []
        raw = await self._client.lrange(self.list_key, after_seq + 1, -1)
        return [json.loads(x) for x in raw]

    async def subscribe(self):
        """实时订阅（比轮询低延迟）。返回 (pubsub, 已缓存事件回放函数)。"""
        pubsub = self._client.pubsub()
        await pubsub.subscribe(self.chan)

        async def replay(after_seq: int):
            return await self.poll_new(after_seq)

        return pubsub, replay
