from datetime import datetime

from sqlalchemy import Integer, String, TIMESTAMP, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(128), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(64))
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1正常 2禁用 3注销")
    joule_gifted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class UserCredential(Base):
    __tablename__ = "user_credentials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    auth_type: Mapped[str] = mapped_column(String(16))
    auth_id: Mapped[str] = mapped_column(String(128))
    __table_args__ = (UniqueConstraint("auth_type", "auth_id", name="uk_type_auth"),)


class AdminUser(Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="super")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class UserPref(Base):
    """用户偏好：创作页记住上次选择的模板。"""
    __tablename__ = "user_prefs"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_template_id: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(),
                                                 onupdate=func.now())


class UserMemory(Base):
    """三层记忆：scope=global(全局偏好)/template(模板专属Skill)/category(分类通用)。

    只存用户偏好文本，永不存文章正文 —— 新创作永远是独立新篇章。
    scope_id 对应模板/分类 id，global 恒为 0。
    """
    __tablename__ = "user_memories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    scope: Mapped[str] = mapped_column(String(16), comment="global|template|category")
    scope_id: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(),
                                                 onupdate=func.now())
    __table_args__ = (UniqueConstraint("user_id", "scope", "scope_id", name="uk_user_scope"),)
