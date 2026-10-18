import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.redis import create_arq_pool
from app.db import get_db
from app.models.template import Template, PromptVersion
from app.models.user import User
from app.models.work import (AiRateCheck, GenerationTask, SearchReference, Work,
                             WorkSegment)
from app.pipelines.followup import FOLLOWUP_PRICE
from app.services import joule, memory
from app.services.events import WorkEvents
from app.services.moderation import check_text

router = APIRouter(prefix="/works", tags=["works"])


class GenerateIn(BaseModel):
    template_id: int
    input: str = Field(min_length=5, max_length=2000)
    response_length: int = Field(default=2, ge=0, le=3)
    enable_think: bool = True
    show_references: bool = True
    material: str = Field(default="", max_length=4000)


@router.post("/generate")
async def generate(body: GenerateIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    tpl = db.get(Template, body.template_id)
    if not tpl or tpl.status != 1:
        raise HTTPException(404, "模板不存在或已下架")
    prompt = (db.query(PromptVersion).filter_by(template_id=tpl.id, published=1)
              .order_by(PromptVersion.version.desc()).first())
    if not prompt:
        raise HTTPException(409, "模板提示词未发布")

    # 输入预检（敏感词），不过不扣费
    verdict = await check_text(db, body.input, "input", user.id)
    if verdict == "block":
        raise HTTPException(422, "输入内容包含违规信息")

    acc = joule.ensure_account(db, user.id)
    if acc.balance < tpl.joule_price:
        raise HTTPException(402, f"焦耳不足（需 {tpl.joule_price}J，余额 {acc.balance}J）")

    work = Work(user_id=user.id, template_id=tpl.id, prompt_version_id=prompt.id,
                topic=body.input, joule_cost=tpl.joule_price,
                params=body.model_dump())
    db.add(work)
    db.flush()
    if not joule.freeze(db, user.id, work.id, tpl.joule_price):
        db.rollback()
        raise HTTPException(402, "焦耳不足")

    # 投递 ARQ（失败必须退款，否则焦耳被冻结卡死、作品永远 pending）
    pool = await create_arq_pool()
    try:
        job = await pool.enqueue_job("generate_work", work.id)
        task = GenerationTask(work_id=work.id, arq_job_id=job.job_id if job else "")
        db.add(task)
        db.commit()
    except Exception:
        db.rollback()
        stuck = db.get(Work, work.id)
        if stuck:
            stuck.status = "failed"
        joule.release(db, work.id, remark="enqueue failed, refunded")
        raise HTTPException(500, "任务投递失败，焦耳已退回，请重试")
    finally:
        await pool.aclose()

    return {"code": 0, "data": {"work_id": work.id, "joule_cost": tpl.joule_price}}


@router.get("/{work_id}/stream")
async def stream(work_id: int, seq: int = 0, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    work = db.get(Work, work_id)
    if not work or work.user_id != user.id:
        raise HTTPException(404, "作品不存在")

    async def gen():
        ev = WorkEvents(work_id)
        last = seq - 1
        idle = 0
        yield "retry: 3000\n\n"
        while True:
            events = await ev.poll_new(last)
            for e in events:
                last = e["seq"]
                data = dict(e["data"])
                data["seq"] = e["seq"]  # 前端记录 lastSeq，追问时从断点续传
                payload = json.dumps(data, ensure_ascii=False)
                yield f"event: {e['event']}\ndata: {payload}\n\n"
                if e["event"] in ("done", "error"):
                    return
            if not events:
                idle += 1
                # 作品已是终态且无新事件 → 补发终止（如 worker 重启后）
                db.expire_all()
                w = db.get(Work, work_id)
                if w and w.status in ("failed", "banned") and idle > 2:
                    yield (f'event: error\ndata: {{"code":"{w.status.upper()}",'
                           '"message":"生成已终止","refunded":true}}\n\n')
                    return
                if idle > 600:  # 5 分钟无事件超时
                    yield 'event: error\ndata: {"code":"STREAM_TIMEOUT"}\n\n'
                    return
                await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.get("")
def list_works(status: str = "", cursor: int = 0, page_size: int = 20,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Work).filter(Work.user_id == user.id)
    if status:
        q = q.filter(Work.status == status)
    if cursor:
        q = q.filter(Work.id < cursor)
    rows = q.order_by(Work.id.desc()).limit(page_size + 1).all()
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    return {"code": 0, "data": {
        "list": [{"work_id": w.id, "title": w.title, "topic": w.topic[:60],
                  "status": w.status, "word_cnt": w.word_cnt,
                  "created_at": str(w.created_at)} for w in rows],
        "cursor": rows[-1].id if has_more else 0, "has_more": has_more}}


@router.get("/{work_id}")
def work_detail(work_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    w = db.get(Work, work_id)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "作品不存在")
    refs = db.query(SearchReference).filter_by(work_id=work_id).order_by(
        SearchReference.idx).all()
    check = (db.query(AiRateCheck).filter_by(work_id=work_id)
             .order_by(AiRateCheck.id.desc()).first())
    tpl = db.get(Template, w.template_id)
    return {"code": 0, "data": {
        "work_id": w.id, "title": w.title, "topic": w.topic, "status": w.status,
        "template_id": w.template_id, "template_name": tpl.name if tpl else "",
        "content_md": w.content_md or "", "word_cnt": w.word_cnt,
        "joule_cost": w.joule_cost, "model_used": w.model_used,
        "references": [{"idx": r.idx, "title": r.title, "url": r.url,
                        "site_name": r.site_name} for r in refs],
        "report": ({"ai_rate": check.ai_rate, "level": check.level}
                   if check else None)}}


@router.get("/{work_id}/versions")
def versions(work_id: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """版本链：V1=初始(body)，其后 followup/regen/edit 依次递增。
    老作品无 segment 时用 work 本身兜底为 V1。"""
    w = db.get(Work, work_id)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "作品不存在")
    segs = (db.query(WorkSegment).filter_by(work_id=work_id)
            .order_by(WorkSegment.turn.asc()).all())
    rows = [{"segment_id": s.id, "turn": s.turn, "role": s.role, "input": s.input,
             "template_id": s.template_id, "content": s.content_md or "",
             "word_cnt": s.word_cnt, "created_at": str(s.created_at)}
            for s in segs if s.content_md]
    if not rows and w.content_md:
        rows = [{"segment_id": 0, "turn": 1, "role": "body", "input": w.topic,
                 "template_id": w.template_id, "content": w.content_md,
                 "word_cnt": w.word_cnt, "created_at": str(w.created_at)}]
    tpl_ids = {r["template_id"] for r in rows if r["template_id"]}
    names = ({t.id: t.name for t in
              db.query(Template).filter(Template.id.in_(tpl_ids)).all()}
             if tpl_ids else {})
    for r in rows:
        r["template_name"] = names.get(r["template_id"], "")
    return {"code": 0, "data": {"versions": rows,
                                "current_turn": rows[-1]["turn"] if rows else 0}}


class ContentIn(BaseModel):
    content_md: str = Field(min_length=1, max_length=30000)


def _save_edit(db: Session, w: Work, content: str, note: str) -> WorkSegment:
    """手动编辑/恢复版本：写 role=edit 的新版本并同步 work 为最新。"""
    last = (db.query(WorkSegment).filter_by(work_id=w.id)
            .order_by(WorkSegment.turn.desc()).first())
    seg = WorkSegment(work_id=w.id, parent_id=last.id if last else None,
                      turn=(last.turn + 1) if last else 2, role="edit", input=note,
                      template_id=w.template_id, content_md=content,
                      word_cnt=len(content))
    db.add(seg)
    w.content_md = content
    w.word_cnt = len(content)
    db.commit()
    return seg


@router.put("/{work_id}/content")
async def edit_content(work_id: int, body: ContentIn,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """直接修改已生成作品全文（免费，生成新版本）。"""
    w = db.get(Work, work_id)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "作品不存在")
    if w.status != "done":
        raise HTTPException(409, "作品尚未完成")
    verdict = await check_text(db, body.content_md, "work", work_id)
    if verdict == "block":
        raise HTTPException(422, "内容未通过安全检测")
    seg = _save_edit(db, w, body.content_md, "手动编辑")
    return {"code": 0, "data": {"turn": seg.turn, "segment_id": seg.id}}


@router.post("/{work_id}/segments/{segment_id}/restore")
async def restore_version(work_id: int, segment_id: int,
                          user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """把某个历史版本恢复为最新版（作为新 edit 版本，免费）。"""
    w = db.get(Work, work_id)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "作品不存在")
    seg = db.get(WorkSegment, segment_id)
    if not seg or seg.work_id != work_id or not seg.content_md:
        raise HTTPException(404, "版本不存在")
    verdict = await check_text(db, seg.content_md, "work", work_id)
    if verdict == "block":
        raise HTTPException(422, "内容未通过安全检测")
    new = _save_edit(db, w, seg.content_md, f"恢复 V{seg.turn}")
    return {"code": 0, "data": {"turn": new.turn, "segment_id": new.id}}


class FollowupIn(BaseModel):
    input: str = Field(min_length=2, max_length=2000)
    remember: bool = False


@router.post("/{work_id}/followup")
async def followup(work_id: int, body: FollowupIn,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """追问改稿：原文+修改要求 → 新版本全文，5J/次；remember=true 沉淀为模板记忆。"""
    w = db.get(Work, work_id)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "作品不存在")
    if w.status != "done":
        raise HTTPException(409, "作品尚未完成")
    if (db.query(GenerationTask).filter_by(work_id=work_id)
            .filter(GenerationTask.status.in_(("queued", "running"))).first()):
        raise HTTPException(409, "上一次生成/修改还在进行中，请稍候")

    verdict = await check_text(db, body.input, "followup", user.id)
    if verdict == "block":
        raise HTTPException(422, "修改要求包含违规信息")

    tpl = db.get(Template, w.template_id)
    prompt = (db.query(PromptVersion).filter_by(template_id=w.template_id, published=1)
              .order_by(PromptVersion.version.desc()).first()) if tpl else None
    if not tpl or not prompt:
        raise HTTPException(409, "模板已下架或提示词未发布，无法修改")

    acc = joule.ensure_account(db, user.id)
    if acc.balance < FOLLOWUP_PRICE:
        raise HTTPException(402, f"焦耳不足（追问需 {FOLLOWUP_PRICE}J）")

    last = (db.query(WorkSegment).filter_by(work_id=work_id)
            .order_by(WorkSegment.turn.desc()).first())
    seg = WorkSegment(work_id=work_id, parent_id=last.id if last else None,
                      turn=(last.turn + 1) if last else 2, role="followup",
                      input=body.input, template_id=w.template_id)
    db.add(seg)
    db.flush()
    if not joule.freeze(db, user.id, work_id * 100000 + seg.id, FOLLOWUP_PRICE):
        db.rollback()
        raise HTTPException(402, "焦耳不足")
    if body.remember:
        memory.append(db, user.id, "template", w.template_id, body.input)

    # 投递 ARQ（失败必须退款；segment 留作意图记录，content 为空不进版本链）
    pool = await create_arq_pool()
    try:
        job = await pool.enqueue_job("followup_work", work_id, seg.id)
        db.add(GenerationTask(work_id=work_id, arq_job_id=job.job_id if job else ""))
        db.commit()
    except Exception:
        db.rollback()
        joule.release(db, work_id * 100000 + seg.id, "enqueue failed, refunded")
        raise HTTPException(500, "任务投递失败，焦耳已退回，请重试")
    finally:
        await pool.aclose()
    await WorkEvents(work_id).emit("stage", {"stage": "queued",
                                             "text": "已收到修改要求，正在排队...",
                                             "turn": seg.turn})
    return {"code": 0, "data": {"segment_id": seg.id, "turn": seg.turn,
                                "joule_cost": FOLLOWUP_PRICE}}
