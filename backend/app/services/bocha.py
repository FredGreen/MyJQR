"""博查 Web Search API：主题 → 3 个子查询 → 参考资料列表。无 key 时跳过。"""
import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

SUBQUERY_TMPL = [
    "{q} 最新进展 2026",
    "{q} 深度分析 观点",
    "{q} 案例 数据",
]


async def search_references(topic: str, count_per_query: int = 3) -> list[dict]:
    s = get_settings()
    if not s.bocha_api_key:
        log.info("BOCHA_API_KEY 未配置，跳过联网搜索")
        return []
    refs: list[dict] = []
    async with httpx.AsyncClient(timeout=20) as client:
        for tmpl in SUBQUERY_TMPL:
            try:
                resp = await client.post(
                    "https://api.bochaai.com/v1/web-search",
                    headers={"Authorization": f"Bearer {s.bocha_api_key}"},
                    json={"query": tmpl.format(q=topic), "summary": True, "count": count_per_query},
                )
                resp.raise_for_status()
                for page in (resp.json().get("data") or {}).get("webPages") or []:
                    refs.append({
                        "title": (page.get("name") or "")[:500],
                        "url": page.get("url") or "",
                        "site_name": page.get("siteName") or "",
                        "summary": (page.get("summary") or "")[:2000],
                    })
            except Exception as e:  # noqa: BLE001
                log.warning("bocha query failed: %r", e)
    # 去重（按 url）
    seen, uniq = set(), []
    for r in refs:
        if r["url"] not in seen:
            seen.add(r["url"])
            uniq.append(r)
    return uniq[:9]
