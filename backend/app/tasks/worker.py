"""ARQ Worker 入口：arq app.tasks.worker.WorkerSettings"""
import logging

from arq import cron

from app.tasks.jobs import generate_work, ping

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


async def fetch_hot_topics(ctx):
    """M4：抓取热点 + Milvus 去重。骨架期空跑。"""
    pass


async def aggregate_stats(ctx):
    """每日聚合 template_stats（use_cnt 已实时累加，此处刷新 user_cnt）。"""
    from sqlalchemy import func, distinct
    from app.db import SessionLocal
    from app.models.work import Work
    from app.models.template import TemplateStat
    db = SessionLocal()
    try:
        rows = (db.query(Work.template_id, func.count(distinct(Work.user_id)))
                .filter(Work.status == "done").group_by(Work.template_id).all())
        for tid, cnt in rows:
            stat = db.get(TemplateStat, tid) or TemplateStat(template_id=tid)
            stat.user_cnt = cnt
            db.merge(stat)
        db.commit()
    finally:
        db.close()


class WorkerSettings:
    functions = [generate_work, ping, fetch_hot_topics, aggregate_stats]
    cron_jobs = [
        cron(fetch_hot_topics, minute=0),
        cron(aggregate_stats, hour=3, minute=0),
    ]
    max_jobs = 20
    job_timeout = 300
    max_tries = 2
    retry_delay = 5
