from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.joule import JouleTransaction, RedeemCode
from app.models.user import User
from app.services import joule

router = APIRouter(prefix="/joule", tags=["joule"])


@router.get("/me")
def balance(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    acc = joule.ensure_account(db, user.id)
    return {"code": 0, "data": {"balance": acc.balance, "frozen": acc.frozen,
                                "total_earned": acc.total_earned,
                                "total_spent": acc.total_spent}}


@router.get("/transactions")
def transactions(cursor: int = 0, page_size: int = 20,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(JouleTransaction).filter(JouleTransaction.user_id == user.id)
    if cursor:
        q = q.filter(JouleTransaction.id < cursor)
    rows = q.order_by(JouleTransaction.id.desc()).limit(page_size + 1).all()
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    return {"code": 0, "data": {
        "list": [{"id": t.id, "biz_type": t.biz_type, "amount": t.amount,
                  "balance_after": t.balance_after, "remark": t.remark,
                  "created_at": str(t.created_at)} for t in rows],
        "cursor": rows[-1].id if has_more else 0, "has_more": has_more}}


class RedeemIn(BaseModel):
    code: str = Field(min_length=8, max_length=16)


@router.post("/redeem")
def redeem(body: RedeemIn, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    rc = db.query(RedeemCode).filter_by(code=body.code.strip()).first()
    if not rc or rc.status != 1:
        raise HTTPException(404, "兑换码无效")
    # 原子核销：status 1→2 抢占
    rows = (db.query(RedeemCode)
            .filter(RedeemCode.id == rc.id, RedeemCode.status == 1)
            .update({"status": 2, "redeemed_by": user.id,
                     "redeemed_at": datetime.now()}))
    if rows == 0:
        db.rollback()
        raise HTTPException(409, "兑换码已被使用")
    joule.credit(db, user.id, rc.amount, "redeem", biz_id=str(rc.id),
                 idem_key=f"redeem:{rc.id}", remark="兑换码充值")
    return {"code": 0, "data": {"amount": rc.amount}}
