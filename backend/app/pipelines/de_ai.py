"""de_ai 工作流：检测原文 → 逐句风险定位 → 定向重写 → 复检（骨架版：整篇重写一轮）。"""
import logging

from sqlalchemy.orm import Session

from app.models.template import Template, PromptVersion
from app.models.work import Work, AiRateCheck
from app.services import joule
from app.services.detector import detect_ai_rate
from app.services.events import WorkEvents
from app.services.llm import stream_chat
from app.services.moderation import check_text

log = logging.getLogger(__name__)


async def run_de_ai(db: Session, work: Work, template: Template,
                    prompt: PromptVersion) -> str:
    ev = WorkEvents(work.id)
    original = work.topic  # 降AI率模板：input 即原文

    await ev.emit("stage", {"stage": "detecting", "text": "正在检测原文 AI 率..."})
    before = detect_ai_rate(original)
    await ev.emit("report", {"ai_rate": before["ai_rate"], "level": before["level"],
                             "phase": "before"})

    await ev.emit("stage", {"stage": "writing", "text": "正在定向重写高风险部分..."})
    pieces: list[str] = []
    async for chunk, result in stream_chat(
            "de_ai_rewrite", system=prompt.system_prompt,
            user=f"以下是原文，请在完全保留信息与观点的前提下重写，降低AI痕迹：\n\n{original}",
            temperature=1.05, max_tokens=8192):
        if chunk:
            pieces.append(chunk)
            await ev.emit("delta", {"text": chunk})
    content = "".join(pieces)
    work.content_md = content
    work.word_cnt = len(content)
    work.model_used = result.model if result else ""
    work.title = "降AI率结果"

    verdict = await check_text(db, content, "work", work.id)
    if verdict == "block":
        work.status = "banned"
        joule.release(db, work.id)
        db.commit()
        await ev.emit("error", {"code": "MODERATION_BLOCK", "refunded": True})
        return "banned"

    after = detect_ai_rate(content)
    db.add(AiRateCheck(work_id=work.id, detector="heuristic", ai_rate=after["ai_rate"],
                       level=after["level"], detail=after["detail"]))
    work.status = "done"
    joule.settle(db, work.id, work.joule_cost)
    db.commit()
    await ev.emit("report", {"ai_rate": after["ai_rate"], "level": after["level"],
                             "phase": "after",
                             "improved": after["ai_rate"] < before["ai_rate"]})
    await ev.emit("done", {"work_id": work.id, "joule_cost": work.joule_cost,
                           "before": before["ai_rate"], "after": after["ai_rate"]})
    return "done"
