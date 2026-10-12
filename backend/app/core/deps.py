from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db import get_db
from app.models.user import User, AdminUser


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    return auth[7:]


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    try:
        payload = verify_token(_bearer(request))
    except Exception:
        raise HTTPException(401, "invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != 1:
        raise HTTPException(401, "user disabled")
    return user


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    try:
        payload = verify_token(_bearer(request), expect_kind="admin")
    except Exception:
        raise HTTPException(401, "invalid or expired token")
    admin = db.get(AdminUser, int(payload["sub"]))
    if not admin:
        raise HTTPException(401, "admin not found")
    return admin
