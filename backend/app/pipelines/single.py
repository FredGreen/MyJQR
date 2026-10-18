"""single 工作流：装配提示词 → (可选)博查 → LLM 流式 → 机审 → AI率检测 → 结算。

由 ARQ worker 调用；所有进度通过 WorkEvents 推给 SSE。
"""
import logging

from sqlalchemy.orm import Session

from app.models.template import Template, PromptVersion, TemplateStat
from app.models.work import Work, SearchReference, AiRateCheck, GenerationTask, WorkSegment
from app.services import joule
from app.services.bocha import search_references
from app.services.detector import detect_ai_rate
from app.services.events import WorkEvents
from app.services.llm import stream_chat
from app.services.memory import build_memory_block
from app.services.moderation import check_text

log = logging.getLogger(__name__)

LENGTH_WORDS = {0: 100, 1: 1200, 2: 2000, 3: 3000}


def render(template: str, **slots) -> str:
    out = template
    for k, v in slots.items():
        out = out.replace("{" + k + "}", str(v if v is not None else ""))
    return out


async def run_single(db: Session, work: Work, template: Template,
                     prompt: PromptVersion) -> str:
    """返回 'done' | 'banned' | 'failed'。"""
    ev = WorkEvents(work.id)
    task = db.query(GenerationTask).filter_by(work_id=work.id).first()
    if task and task.status == "queued":
        from datetime import datetime as _dt
        task.status, task.started_at = "running", _dt.now()

    params = work.params or {}
    length_words = LENGTH_WORDS.get(params.get("response_length", 2), 2000)
    route = "think" if (template.enable_think and params.get("enable_think", True)) \
        else (template.model_route or "default_chat")

    # ① 联网搜索（服务端默认动作；无 key 静默跳过）
    refs: list[dict] = []
    if template.enable_web_search:
        await ev.emit("stage", {"stage": "searching", "text": "正在联网检索资料..."})
        refs = await search_references(work.topic)
        for i, r in enumerate(refs):
            db.add(SearchReference(work_id=work.id, idx=i + 1, title=r["title"],
                                   url=r["url"], site_name=r["site_name"], summary=r["summary"]))
        db.commit()
        await ev.emit("search_end", {"references": refs} if params.get("show_references", False)
                      else {"count": len(refs)})

    # ② 装配提示词
    await ev.emit("stage", {"stage": "outlining", "text": "正在构思大纲与文风..."})
    ref_block = "\n".join(f"[{i+1}] {r['title']} —— {r['summary'][:120]}"
                          for i, r in enumerate(refs)) or "（无）"
    user_prompt = render(prompt.user_prompt_template, topic=work.topic,
                         material=params.get("material", ""), length=length_words)
    user_prompt += f"\n\n参考资料（仅供背景，禁止照抄，禁止在文中标注来源编号）：\n{ref_block}"
    # 三层记忆（全局偏好/分类通用/模板专属）：只注入偏好文本，不加载历史文章
    memory_block = build_memory_block(db, work.user_id, template)

    # ③ LLM 流式
    await ev.emit("stage", {"stage": "writing", "text": "正在撰写全文..."})
    pieces: list[str] = []
    final = None
    async for chunk, result in stream_chat(
            route, system=prompt.system_prompt + memory_block, user=user_prompt,
            temperature=float(template.temperature or 0.9),
            max_tokens=template.max_tokens or 8192):
        if chunk:
            pieces.append(chunk)
            await ev.emit("delta", {"text": chunk})
        elif result:
            final = result
    content = "".join(pieces)
    work.content_md = content
    work.word_cnt = len(content)
    work.model_used = final.model if final else ""
    work.tokens_in, work.tokens_out = (final.tokens_in, final.tokens_out) if final else (0, 0)

    # ④ 内容机审（先审后显）
    await ev.emit("stage", {"stage": "moderating", "text": "内容安全检测中..."})
    verdict = await check_text(db, content, "work", work.id)
    if verdict == "block":
        from datetime import datetime as _dt
        work.status = "banned"
        joule.release(db, work.id, "moderation blocked")
        if task:
            task.status, task.finished_at, task.error_code = "failed", _dt.now(), "MODERATION_BLOCK"
        db.commit()
        await ev.emit("error", {"code": "MODERATION_BLOCK",
                                "message": "生成内容未通过安全检测，焦耳已退回", "refunded": True})
        return "banned"

    # ⑤ AI 率检测
    await ev.emit("stage", {"stage": "detecting", "text": "AI 率检测中..."})
    rep = detect_ai_rate(content)
    db.add(AiRateCheck(work_id=work.id, detector="heuristic",
                       ai_rate=rep["ai_rate"], level=rep["level"], detail=rep["detail"]))
    first_line = next((l.strip().lstrip("#").strip("*").strip()
                       for l in content.splitlines() if l.strip()), "")
    work.title = first_line[:120]
    work.status = "done"
    # 初始版本入版本链（V1=body；老作品无 segment，versions 接口用 work 兜底）
    if not db.query(WorkSegment).filter_by(work_id=work.id).first():
        db.add(WorkSegment(work_id=work.id, turn=1, role="body", input=work.topic,
                           content_md=content, word_cnt=work.word_cnt))
    joule.settle(db, work.id, work.joule_cost)
    stat = db.get(TemplateStat, template.id) or TemplateStat(template_id=template.id)
    stat.use_cnt = (stat.use_cnt or 0) + 1  # 新建对象 flush 前是 None，直接 += 会炸
    db.merge(stat)
    if task:
        from datetime import datetime as _dt
        task.status, task.finished_at = "success", _dt.now()
    db.commit()

    free_rewrite = rep["ai_rate"] >= 80
    await ev.emit("report", {"ai_rate": rep["ai_rate"], "level": rep["level"],
                             "rewrite_free": free_rewrite,
                             "risky_sentences": rep["detail"].get("risky_sentences", [])})
    await ev.emit("done", {"work_id": work.id, "joule_cost": work.joule_cost,
                           "word_cnt": work.word_cnt, "model": work.model_used})
    return "done"
