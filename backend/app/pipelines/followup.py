"""追问（改稿）工作流：原文 + 修改要求 → 流式输出修改后全文。

上下文固定 4 条消息（原始指令 / 当前全文 / 本次要求），连续追问只带最新版，
不随轮次膨胀。事件复用 works:{id} SSE 通道，payload 带 turn 区分版本。
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.template import Template, PromptVersion
from app.models.work import Work, GenerationTask, WorkSegment
from app.pipelines.single import LENGTH_WORDS, render
from app.services import joule
from app.services.events import WorkEvents
from app.services.llm import stream_chat
from app.services.memory import build_memory_block
from app.services.moderation import check_text

log = logging.getLogger(__name__)

FOLLOWUP_PRICE = 5

FOLLOWUP_SYSTEM_SUFFIX = (
    "\n\n【改稿模式】用户已有一篇按上述设定生成的文章，接下来会给出修改要求。"
    "请输出修改后的完整文章：未被要求改动的部分保持原样，落实全部修改要求；"
    "不要输出任何解释、 diff 或修改说明，直接输出正文。"
)


def latest_content(db: Session, work: Work, exclude_id: int = 0) -> str:
    """最新已生成版本全文（不含 exclude_id 指定段）；无任何 segment 时用 work 兜底。"""
    q = (db.query(WorkSegment)
         .filter(WorkSegment.work_id == work.id,
                 WorkSegment.content_md.isnot(None)))
    if exclude_id:
        q = q.filter(WorkSegment.id != exclude_id)
    seg = q.order_by(WorkSegment.turn.desc()).first()
    if seg and seg.content_md:
        return seg.content_md
    return work.content_md or ""


def build_messages(db: Session, work: Work, seg: WorkSegment, template: Template,
                   prompt: PromptVersion) -> list[dict]:
    params = work.params or {}
    length_words = LENGTH_WORDS.get(params.get("response_length", 2), 2000)
    orig_user = render(prompt.user_prompt_template, topic=work.topic,
                       material=params.get("material", ""), length=length_words)
    current = latest_content(db, work, exclude_id=seg.id)
    memory_block = build_memory_block(db, work.user_id, template)
    return [
        {"role": "system", "content": prompt.system_prompt + memory_block
            + FOLLOWUP_SYSTEM_SUFFIX},
        {"role": "user", "content": orig_user},
        {"role": "assistant", "content": current},
        {"role": "user", "content": f"修改要求：{seg.input}\n请输出修改后的完整文章。"},
    ]


async def run_followup(db: Session, work: Work, seg: WorkSegment, template: Template,
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
    messages = build_messages(db, work, seg, template, prompt)

    await ev.emit("stage", {"stage": "writing", "text": "正在按你的要求修改...", "turn": turn})
    pieces: list[str] = []
    final = None
    async for chunk, result in stream_chat(
            template.model_route or "default_chat", messages=messages,
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

    # 先审后显：不过审则回滚（work 保持修改前版本）并退款
    await ev.emit("stage", {"stage": "moderating", "text": "内容安全检测中...", "turn": turn})
    verdict = await check_text(db, content, "followup", seg.id)
    if verdict == "block":
        seg.content_md = None
        seg.word_cnt = 0
        joule.release(db, freeze_key, "moderation blocked")
        if task:
            task.status, task.finished_at, task.error_code = "failed", datetime.now(), \
                "MODERATION_BLOCK"
        db.commit()
        await ev.emit("error", {"code": "MODERATION_BLOCK", "turn": turn,
                                "message": "修改内容未通过安全检测，焦耳已退回",
                                "refunded": True})
        return "banned"

    work.content_md = content
    work.word_cnt = len(content)
    work.joule_cost = (work.joule_cost or 0) + FOLLOWUP_PRICE
    joule.settle(db, freeze_key, FOLLOWUP_PRICE, biz_type="followup")
    if task:
        task.status, task.finished_at = "success", datetime.now()
    db.commit()

    await ev.emit("done", {"work_id": work.id, "turn": turn, "segment_id": seg.id,
                           "word_cnt": work.word_cnt, "joule_cost": FOLLOWUP_PRICE,
                           "model": work.model_used})
    return "done"
