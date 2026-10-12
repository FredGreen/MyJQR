from datetime import datetime

from sqlalchemy import (JSON, Date, DateTime, Index, Integer, String, Text,
                        TIMESTAMP, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HotTopic(Base):
    __tablename__ = "hot_topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(32), default="internal")
    source_url: Mapped[str] = mapped_column(String(1024), default="")
    heat: Mapped[int] = mapped_column(Integer, default=0)
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fetched_date: Mapped[datetime] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    __table_args__ = (Index("idx_date", "fetched_date"), Index("idx_heat", "heat"))


class SensitiveWord(Base):
    __tablename__ = "sensitive_words"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(64), unique=True)
    level: Mapped[int] = mapped_column(Integer, comment="1拦截 2复审 3替换")
    replace_to: Mapped[str] = mapped_column(String(32), default="＊")


class ContentModeration(Base):
    __tablename__ = "content_moderations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    biz_type: Mapped[str] = mapped_column(String(16), comment="input|work|followup")
    biz_id: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(24), default="aliyun")
    verdict: Mapped[str] = mapped_column(String(16), comment="pass|review|block")
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    __table_args__ = (Index("idx_verdict", "verdict", "biz_type"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(64), default="")
    diff: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
