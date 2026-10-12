"""JWT RS256 签发/校验；密钥对首次运行自动生成。密码用 PBKDF2-SHA256（无外部依赖）。"""
import hashlib
import os
import secrets
import time
from pathlib import Path

import jwt

from app.core.config import get_settings

_ALG = "RS256"
ACCESS_TTL = 2 * 3600
REFRESH_TTL = 30 * 24 * 3600
_ITER = 200_000


def _ensure_keys() -> tuple[str, str]:
    s = get_settings()
    priv, pub = Path(s.jwt_private_pem), Path(s.jwt_public_pem)
    if not priv.exists():
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv.parent.mkdir(parents=True, exist_ok=True)
        priv.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        pub.write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return priv.read_text(), pub.read_text()


def issue_tokens(sub: str, kind: str = "user") -> dict:
    priv, _ = _ensure_keys()
    now = int(time.time())
    base = {"sub": sub, "kind": kind, "iat": now}
    access = jwt.encode({**base, "exp": now + ACCESS_TTL, "t": "access"}, priv, algorithm=_ALG)
    refresh = jwt.encode({**base, "exp": now + REFRESH_TTL, "t": "refresh"}, priv, algorithm=_ALG)
    return {"access_token": access, "refresh_token": refresh,
            "token_type": "bearer", "expires_in": ACCESS_TTL}


def verify_token(token: str, expect_t: str = "access", expect_kind: str = "user") -> dict:
    _, pub = _ensure_keys()
    payload = jwt.decode(token, pub, algorithms=[_ALG])
    if payload.get("t") != expect_t or payload.get("kind") != expect_kind:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


# ---- 密码 ----
def hash_password(raw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt.encode(), _ITER).hex()
    return f"pbkdf2${salt}${dk}"


def verify_password(raw: str, stored: str) -> bool:
    try:
        _, salt, dk = stored.split("$")
    except ValueError:
        return False
    cand = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt.encode(), _ITER).hex()
    return secrets.compare_digest(cand, dk)
