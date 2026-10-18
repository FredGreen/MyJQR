"""焦耳账本：两阶段扣费（冻结→结算/解冻），全程幂等。"""
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.joule import JouleAccount, JouleTransaction, JouleFreeze

log = logging.getLogger(__name__)


def ensure_account(db: Session, user_id: int) -> JouleAccount:
    acc = db.query(JouleAccount).filter_by(user_id=user_id).first()
    if not acc:
        acc = JouleAccount(user_id=user_id)
        db.add(acc)
        db.commit()
    return acc


def _record(db: Session, user_id: int, biz_type: str, amount: int, balance_after: int,
            biz_id: str, idem_key: str, remark: str = ""):
    if db.query(JouleTransaction).filter_by(idempotency_key=idem_key).first():
        return False  # 已入账（幂等）
    db.add(JouleTransaction(user_id=user_id, biz_type=biz_type, amount=amount,
                            balance_after=balance_after, biz_id=biz_id,
                            idempotency_key=idem_key, remark=remark))
    return True


def credit(db: Session, user_id: int, amount: int, biz_type: str, biz_id: str = "",
           idem_key: str = "", remark: str = "") -> bool:
    acc = ensure_account(db, user_id)
    acc.balance += amount
    acc.total_earned += amount
    db.flush()
    key = idem_key or f"{biz_type}:{biz_id}:{user_id}"
    ok = _record(db, user_id, biz_type, amount, acc.balance, biz_id, key, remark)
    db.commit()
    return ok


def freeze(db: Session, user_id: int, work_id: int, amount: int) -> bool:
    """余额充足则冻结；返回 False 表示余额不足。"""
    row = db.execute(
        text("UPDATE joule_accounts SET balance=balance-:a, frozen=frozen+:a "
             "WHERE user_id=:u AND balance>=:a"),
        {"a": amount, "u": user_id},
    )
    if row.rowcount == 0:
        db.rollback()
        return False
    db.add(JouleFreeze(user_id=user_id, work_id=work_id, amount=amount, status=1))
    db.commit()
    return True


def settle(db: Session, work_id: int, amount: int, remark: str = "",
           biz_type: str = "generate"):
    """成功：冻结转扣减。幂等键 work:work_id:settle（work_id 即冻结键）。"""
    fz = db.query(JouleFreeze).filter_by(work_id=work_id, status=1).first()
    if not fz:
        return
    db.execute(text("UPDATE joule_accounts SET frozen=frozen-:a, total_spent=total_spent+:a "
                    "WHERE user_id=:u"), {"a": amount, "u": fz.user_id})
    fz.status, fz.settled_at = 2, datetime.now()
    acc = ensure_account(db, fz.user_id)
    _record(db, fz.user_id, biz_type, -amount, acc.balance, str(work_id),
            f"work:{work_id}:settle", remark)
    db.commit()


def release(db: Session, work_id: int, remark: str = "generation failed, refunded"):
    """失败：解冻退回。幂等键 work:work_id:release。"""
    fz = db.query(JouleFreeze).filter_by(work_id=work_id, status=1).first()
    if not fz:
        return
    db.execute(text("UPDATE joule_accounts SET balance=balance+:a, frozen=frozen-:a "
                    "WHERE user_id=:u"), {"a": fz.amount, "u": fz.user_id})
    fz.status, fz.settled_at = 3, datetime.now()
    acc = ensure_account(db, fz.user_id)
    _record(db, fz.user_id, "refund", fz.amount, acc.balance, str(work_id),
            f"work:{work_id}:release", remark)
    db.commit()
