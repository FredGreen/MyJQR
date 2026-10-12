from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class JouleAccount(Base):
    __tablename__ = "joule_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    frozen: Mapped[int] = mapped_column(Integer, default=0)
    total_earned: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[int] = mapped_column(Integer, default=0)


class JouleTransaction(Base):
    __tablename__ = "joule_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    biz_type: Mapped[str] = mapped_column(String(24))
    amount: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    biz_id: Mapped[str] = mapped_column(String(64), default="")
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    remark: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    __table_args__ = (Index("idx_user_time", "user_id", "created_at"),)


class JouleFreeze(Base):
    __tablename__ = "joule_freezes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    work_id: Mapped[int] = mapped_column(Integer, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1冻结 2已结算 3已解冻")
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RedeemCode(Base):
    __tablename__ = "redeem_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    batch_no: Mapped[str] = mapped_column(String(32), default="")
    redeemed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1未用 2已用 3作废")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
