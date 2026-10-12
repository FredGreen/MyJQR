from datetime import datetime

from sqlalchemy import (JSON, DECIMAL, Index, Integer, String, TIMESTAMP, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    icon: Mapped[str] = mapped_column(String(512), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)


class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(String(500), default="")
    author_id: Mapped[int] = mapped_column(Integer, default=0, comment="0=官方")
    workflow_type: Mapped[str] = mapped_column(String(24), default="single")
    model_route: Mapped[str] = mapped_column(String(32), default="default_chat")
    enable_web_search: Mapped[int] = mapped_column(Integer, default=1)
    enable_think: Mapped[int] = mapped_column(Integer, default=1)
    temperature: Mapped[float] = mapped_column(DECIMAL(3, 2), default=0.95)
    max_tokens: Mapped[int] = mapped_column(Integer, default=8192)
    response_length: Mapped[int] = mapped_column(Integer, default=2, comment="1短2中3长")
    output_format: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    usage_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage_tips: Mapped[str | None] = mapped_column(Text, nullable=True)
    joule_price: Mapped[int] = mapped_column(Integer, default=1000)
    score: Mapped[float] = mapped_column(DECIMAL(2, 1), default=5.0)
    status: Mapped[int] = mapped_column(Integer, default=0, comment="0草稿 1上线 2下架")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index("idx_status_sort", "status", "sort_order"),)


class TemplateCategoryRelation(Base):
    __tablename__ = "template_category_relations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[int] = mapped_column(Integer)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        UniqueConstraint("template_id", "category_id", name="uk_tpl_cat"),
        Index("idx_cat_rank", "category_id", "rank"),
    )


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    system_prompt: Mapped[str] = mapped_column(Text)
    user_prompt_template: Mapped[str] = mapped_column(Text,
        default="主题：{topic}\n素材：{material}\n字数：约{length}字")
    ai_word_blacklist: Mapped[list | None] = mapped_column(JSON, nullable=True)
    eval_score: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    published: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    __table_args__ = (UniqueConstraint("template_id", "version", name="uk_tpl_ver"),)


class TemplateStat(Base):
    __tablename__ = "template_stats"
    template_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_cnt: Mapped[int] = mapped_column(Integer, default=0)
    use_cnt: Mapped[int] = mapped_column(Integer, default=0)
    rewrite_cnt: Mapped[int] = mapped_column(Integer, default=0)
    bookmark_cnt: Mapped[int] = mapped_column(Integer, default=0)


class Bookmark(Base):
    __tablename__ = "bookmarks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    template_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "template_id", name="uk_user_tpl"),)
