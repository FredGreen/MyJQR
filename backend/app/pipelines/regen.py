"""换模板重生成：同一主题/素材，用新模板的提示词与参数重写整篇，作为新版本。

参考资料复用初始生成时已入库的 SearchReference，不重复联网搜索；
完成后 work 切换到新模板（后续追问跟随新模板），AI 率检测挂 segment_id。
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.joule import JouleFreeze
from app.models.template import Template, PromptVersion, TemplateStat
from app.models.work import Work, GenerationTask, SearchReference, AiRateCheck, WorkSegment
from app.pipelines.single import LENGTH_WORDS, render
from app.services import joule
from app.services.detector import detect_ai_rate
from app.services.events import WorkEvents
from app.services.llm import stream_chat
from app.services.memory import build_memory_block
from app.services.moderation import check_text

log = logging.getLogger(__name__)


async def run_regen(db: Session, work: Work, seg: WorkSegment, template: Template,
                    prompt: PromptVersion) -> str:
    """返回 'done' | 'banned' | 'failed'。"""
    ev = WorkEvents(work.id)
    turn = seg.turn
    task = (db.query(GenerationTask).filter_by(work_id=work.id)
            .order_by(GenerationTask.id.desc()).first())
    if task and task.status == "queued":
        task.status, task.started_at = "running", datetime.now()
        db.commit()

    freeze_key = work.id * 100000 + seg.id
    fz = db.query(JouleFreeze).filter_by(work_id=freeze_key, status=1).first()
    price = fz.amount if fz else 0

    params = work.params or {}
    length_words = LENGTH_WORDS.get(params.get("response_length", 2), 2000)
    route = "think" if (template.enable_think and params.get("enable_think", True)) \
        else (template.model_route or "default_chat")

    refs = (db.query(SearchReference).filter_by(work_id=work.id)
            .order_by(SearchReference.idx).all())
    ref_block = "\n".join(f"[{r.idx}] {r.title} —— {(r.summary or '')[:120]}"
                          for r in refs) or "（无）"
    user_prompt = render(prompt.user_prompt_template, topic=work.topic,
                         material=params.get("material", ""), length=length_words)
    user_prompt += f"\n\n参考资料（仅供背景，禁止照抄，禁止在文中标注来源编号）：\n{ref_block}"
    # 记忆块跟随新模板（新模板的模板层 + 其分类层 + 全局层）
    system_prompt = prompt.system_prompt + build_memory_block(db, work.user_id, template)

    await ev.emit("stage", {"stage": "writing",
                            "text": f"正在用「{template.name}」重新创作...", "turn": turn})
    pieces: list[str] = []
    final = None
    async for chunk, result in stream_chat(
            route, system=system_prompt, user=user_prompt,
            temperature=float(template.temperature or 0.9),
            max_tokens=template.max_tokens or 8192):
        if chunk:
            pieces.append(chunk)
            await ev.emit("delta", {"text": chunk, "turn": turn})
        elif result:
            final = result
    content = "".join(pieces)
    seg.content_md = content
    seg.word_cnt = len(content)
    if final:
        work.model_used = final.model

    await ev.emit("stage", {"stage": "moderating", "text": "内容安全检测中...", "turn": turn})
    verdict = await check_text(db, content, "work", work.id)
    if verdict == "block":
        seg.content_md = None
        seg.word_cnt = 0
        joule.release(db, freeze_key, "moderation blocked")
        if task:
            task.status, task.finished_at, task.error_code = "failed", datetime.now(), \
                "MODERATION_BLOCK"
        db.commit()
        await ev.emit("error", {"code": "MODERATION_BLOCK", "turn": turn,
                                "message": "生成内容未通过安全检测，焦耳已退回",
                                "refunded": True})
        return "banned"

    # AI 率检测（挂 segment_id，报告随版本）
    await ev.emit("stage", {"stage": "detecting", "text": "AI 率检测中...", "turn": turn})
    rep = detect_ai_rate(content)
    db.add(AiRateCheck(work_id=work.id, segment_id=seg.id, detector="heuristic",
                       ai_rate=rep["ai_rate"], level=rep["level"], detail=rep["detail"]))

    first_line = next((l.lstrip("# ").strip() for l in content.splitlines() if l.strip()), "")
    work.title = first_line[:120]
    work.content_md = content
    work.word_cnt = len(content)
    work.template_id = template.id
    work.prompt_version_id = prompt.id
    work.joule_cost = (work.joule_cost or 0) + price
    joule.settle(db, freeze_key, price)
    stat = db.get(TemplateStat, template.id) or TemplateStat(template_id=template.id)
    stat.use_cnt = (stat.use_cnt or 0) + 1
    db.merge(stat)
    if task:
        task.status, task.finished_at = "success", datetime.now()
    db.commit()

    await ev.emit("report", {"ai_rate": rep["ai_rate"], "level": rep["level"],
                             "turn": turn,
                             "risky_sentences": rep["detail"].get("risky_sentences", [])})
    await ev.emit("done", {"work_id": work.id, "turn": turn, "segment_id": seg.id,
                           "template_id": template.id, "template_name": template.name,
                           "word_cnt": work.word_cnt, "joule_cost": price,
                           "model": work.model_used})
    return "done"
