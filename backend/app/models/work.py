from datetime import datetime

from sqlalchemy import (JSON, DateTime, Index, Integer, String, TIMESTAMP, Text, func)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Work(Base):
    __tablename__ = "works"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    template_id: Mapped[int] = mapped_column(Integer)
    prompt_version_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(128), default="")
    topic: Mapped[str] = mapped_column(String(1000))
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_md: Mapped[str | None] = mapped_column(MEDIUMTEXT, nullable=True)
    content_rich: Mapped[str | None] = mapped_column(MEDIUMTEXT, nullable=True)
    word_cnt: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="generating",
                                        comment="generating|detecting|done|failed|banned")
    joule_cost: Mapped[int] = mapped_column(Integer, default=0)
    model_used: Mapped[str] = mapped_column(String(32), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index("idx_user_time", "user_id", "created_at"), Index("idx_status", "status"))


class WorkSegment(Base):
    __tablename__ = "work_segments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turn: Mapped[int] = mapped_column(Integer, default=1)
    role: Mapped[str] = mapped_column(String(16), comment="body|followup|regen|edit")
    input: Mapped[str] = mapped_column(String(2000), default="")
    template_id: Mapped[int] = mapped_column(Integer, default=0, comment="regen 版本记录来源模板")
    word_cnt: Mapped[int] = mapped_column(Integer, default=0)
    content_md: Mapped[str | None] = mapped_column(MEDIUMTEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    __table_args__ = (Index("idx_work_turn", "work_id", "turn"),)


class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(Integer, index=True)
    arq_job_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="queued")
    error_code: Mapped[str] = mapped_column(String(32), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class SearchReference(Base):
    __tablename__ = "search_references"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(Integer)
    idx: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(512), default="")
    url: Mapped[str] = mapped_column(String(1024), default="")
    site_name: Mapped[str] = mapped_column(String(128), default="")
    summary: Mapped[str] = mapped_column(String(2000), default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (Index("idx_work_idx", "work_id", "idx"),)


class AiRateCheck(Base):
    __tablename__ = "ai_rate_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(Integer)
    segment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detector: Mapped[str] = mapped_column(String(16), default="heuristic")
    ai_rate: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(8), comment="human|suspect|ai")
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    __table_args__ = (Index("idx_work_time", "work_id", "created_at"),)
