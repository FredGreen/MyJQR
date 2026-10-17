"""LLM 网关：DeepSeek / GLM 统一 OpenAI 兼容协议，流式输出，路由表 + fallback。

不依赖 openai SDK，直接用 httpx 解析 SSE，方便控制与计量。
"""
import logging
from dataclasses import dataclass
from typing import AsyncIterator

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)


@dataclass
class LLMResult:
    text: str
    model: str
    tokens_in: int
    tokens_out: int


class LLMError(Exception):
    pass


def _resolve(route_key: str) -> list[tuple[str, str]]:
    s = get_settings()
    p, m, fp, fm = s.MODEL_ROUTES.get(route_key, s.MODEL_ROUTES["default_chat"])
    chain = [(p, m)]
    if (fp, fm) != (p, m):
        chain.append((fp, fm))
    return [(provider, model) for provider, model in chain
            if s.llm_providers.get(provider, {}).get("api_key")]


async def stream_chat(route_key: str, system: str, user: str, *, temperature: float = 0.9,
                      max_tokens: int = 8192) -> AsyncIterator[tuple[str, LLMResult]]:
    """yield (增量文本, None)；结束时 yield ("", LLMResult)。按路由降级链尝试。"""
    s = get_settings()
    chain = _resolve(route_key)
    if not chain:
        raise LLMError("no provider available: set DEEPSEEK_API_KEY / ZHIPU_API_KEY")

    last_err: Exception | None = None
    for provider, model in chain:
        try:
            acc, tin, tout = [], 0, 0
            async for chunk, usage in _stream_once(
                    s.llm_providers[provider], model, system, user, temperature, max_tokens):
                if chunk:
                    acc.append(chunk)
                    yield chunk, None
                if usage:
                    tin, tout = usage
            yield "", LLMResult("".join(acc), model, tin, tout)
            return
        except Exception as e:  # noqa: BLE001 —— 任何失败换 fallback
            last_err = e
            log.warning("provider %s/%s failed: %r, trying fallback", provider, model, e)
    raise LLMError(f"all providers failed: {last_err!r}")


async def _stream_once(conf: dict, model: str, system: str, user: str,
                       temperature: float, max_tokens: int):
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    usage = None
    timeout = httpx.Timeout(connect=15, read=180, write=30, pool=15)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # 流式必须用 client.stream()（它才是异步上下文管理器；client.post 返回 coroutine）
        async with client.stream("POST", f"{conf['base_url']}/chat/completions",
                                 headers={"Authorization": f"Bearer {conf['api_key']}"},
                                 json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    import json
                    obj = json.loads(data)
                except ValueError:
                    continue
                if obj.get("usage"):
                    u = obj["usage"]
                    usage = (u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
                choices = obj.get("choices") or []
                if choices:
                    # deepseek-reasoner 的 reasoning_content 不外发
                    delta = choices[0].get("delta", {}) or {}
                    piece = delta.get("content") or ""
                    if piece:
                        yield piece, None
    yield "", usage
