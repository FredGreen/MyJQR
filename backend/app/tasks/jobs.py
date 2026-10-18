"""ARQ 任务函数（worker 进程内执行，注意：每个任务自管 DB 会话与事件流）。"""
import logging
from datetime import date, datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.models.template import Template, PromptVersion
from app.models.work import Work, GenerationTask, WorkSegment
from app.pipelines.single import run_single
from app.services import joule
from app.services.events import WorkEvents

log = logging.getLogger(__name__)


async def _run_de_ai(db, work, template, prompt):
    from app.pipelines.de_ai import run_de_ai
    return await run_de_ai(db, work, template, prompt)


async def generate_work(ctx, work_id: int) -> str:
    db = SessionLocal()
    ev = WorkEvents(work_id)
    try:
        work = db.get(Work, work_id)
        if not work:
            return "missing"
        template = db.get(Template, work.template_id)
        prompt = (db.query(PromptVersion)
                  .filter_by(template_id=work.template_id, published=1)
                  .order_by(PromptVersion.version.desc()).first())
        if not template or not prompt:
            work.status = "failed"
            joule.release(db, work_id, "template/prompt missing")
            db.commit()
            await ev.emit("error", {"code": "TEMPLATE_MISSING", "refunded": True})
            return "failed"

        result = await run_single(db, work, template, prompt) \
            if template.workflow_type != "de_ai" else \
            await _run_de_ai(db, work, template, prompt)
        return result
    except Exception as e:  # noqa: BLE001 —— 兜底：标记失败 + 退款 + 错误事件
        log.exception("generate_work %s failed", work_id)
        db.rollback()
        work = db.get(Work, work_id)
        if work:
            work.status = "failed"
            db.commit()
        joule.release(db, work_id)
        task = db.query(GenerationTask).filter_by(work_id=work_id).first()
        if task:
            task.status, task.finished_at, task.error_code = "failed", datetime.now(), "INTERNAL"
            db.commit()
        await ev.emit("error", {"code": "INTERNAL", "message": str(e)[:200], "refunded": True})
        return "failed"
    finally:
        db.close()


async def followup_work(ctx, work_id: int, segment_id: int) -> str:
    """追问改稿：失败兜底退款，并把 work 恢复为最后一份可用版本。"""
    db = SessionLocal()
    ev = WorkEvents(work_id)
    freeze_key = work_id * 100000 + segment_id
    try:
        work = db.get(Work, work_id)
        seg = db.get(WorkSegment, segment_id)
        if not work or not seg or seg.work_id != work_id:
            return "missing"
        turn = seg.turn
        template = db.get(Template, work.template_id)
        prompt = (db.query(PromptVersion)
                  .filter_by(template_id=work.template_id, published=1)
                  .order_by(PromptVersion.version.desc()).first())
        if not template or not prompt:
            joule.release(db, freeze_key, "template/prompt missing")
            db.commit()
            await ev.emit("error", {"code": "TEMPLATE_MISSING", "refunded": True,
                                    "turn": turn})
            return "failed"

        from app.pipelines.followup import run_followup
        return await run_followup(db, work, seg, template, prompt)
    except Exception as e:  # noqa: BLE001 —— 兜底：回滚正文 + 退款 + 错误事件
        log.exception("followup_work %s/%s failed", work_id, segment_id)
        db.rollback()
        seg = db.get(WorkSegment, segment_id)
        turn = seg.turn if seg else 0
        if seg:
            seg.content_md = None
            seg.word_cnt = 0
        work = db.get(Work, work_id)
        if work:
            from app.pipelines.followup import latest_content
            work.content_md = latest_content(db, work, exclude_id=segment_id)
        joule.release(db, freeze_key)
        task = (db.query(GenerationTask).filter_by(work_id=work_id)
                .order_by(GenerationTask.id.desc()).first())
        if task and task.status in ("queued", "running"):
            task.status, task.finished_at, task.error_code = "failed", datetime.now(), "INTERNAL"
        db.commit()
        await ev.emit("error", {"code": "INTERNAL", "message": str(e)[:200],
                                "refunded": True, "turn": turn})
        return "failed"
    finally:
        db.close()


async def ping(ctx) -> str:
    return "pong"
