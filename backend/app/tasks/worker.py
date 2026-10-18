"""ARQ Worker 入口：arq app.tasks.worker.WorkerSettings"""
import logging

from arq import cron

from app.core.redis import arq_redis_settings
from app.tasks.jobs import followup_work, generate_work, ping, regen_work

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
    functions = [generate_work, followup_work, regen_work, ping, fetch_hot_topics,
                 aggregate_stats]
    # 从 .env 的 REDIS_URL 读取并放宽连接超时（见 app/core/redis.py）；
    # 不配则 ARQ 默认 localhost:6379，.env 改了也不生效
    redis_settings = arq_redis_settings()
    redis_settings.conn_retries = 10
    cron_jobs = [
        cron(fetch_hot_topics, minute=0),
        cron(aggregate_stats, hour=3, minute=0),
    ]
    max_jobs = 20
    job_timeout = 300
    max_tries = 2
    retry_delay = 5
