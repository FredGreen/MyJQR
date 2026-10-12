from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import hash_password, issue_tokens, verify_password, verify_token
from app.db import get_db
from app.models.user import User, UserCredential
from app.models.joule import JouleAccount
from app.services import joule

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(min_length=1, max_length=32)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(409, "邮箱已注册")
    user = User(email=body.email, password_hash=hash_password(body.password),
                nickname=body.nickname)
    db.add(user)
    db.flush()
    db.add(UserCredential(user_id=user.id, auth_type="email", auth_id=body.email))
    db.commit()
    # 新人礼
    joule.credit(db, user.id, get_settings().signup_gift_joule, "gift",
                 biz_id=str(user.id), idem_key=f"signup_gift:{user.id}",
                 remark="新人注册赠送")
    user.joule_gifted = 1
    db.commit()
    return {"code": 0, "data": {"id": user.id, "tokens": issue_tokens(str(user.id))}}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "邮箱或密码错误")
    if user.status != 1:
        raise HTTPException(403, "账号已禁用")
    return {"code": 0, "data": {"id": user.id, "nickname": user.nickname,
                                "tokens": issue_tokens(str(user.id))}}


@router.post("/refresh")
def refresh(body: RefreshIn):
    try:
        payload = verify_token(body.refresh_token, expect_t="refresh")
    except Exception:
        raise HTTPException(401, "refresh_token 无效")
    return {"code": 0, "data": issue_tokens(payload["sub"])}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    acc = joule.ensure_account(db, user.id)
    return {"code": 0, "data": {"id": user.id, "email": user.email,
                                "nickname": user.nickname, "avatar_url": user.avatar_url,
                                "joule": {"balance": acc.balance, "frozen": acc.frozen}}}


@router.delete("/account")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.status = 3
    user.email = f"deleted_{user.id}@invalid"
    db.commit()
    return {"code": 0, "data": "account deleted"}
