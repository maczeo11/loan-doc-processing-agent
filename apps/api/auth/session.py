"""Stateless HS256 session JWT (short TTL). No Redis sessions (transient only)."""

import datetime
from typing import Dict, Any
from apps.api.config import settings


def _secret() -> str:
    s = settings.JWT_SECRET or ""
    if settings.ENVIRONMENT in ("cloud", "production") and (not s or s == "dev-only-insecure-secret-change-me"):
        raise RuntimeError("JWT_SECRET must be set in cloud/production")
    return s or "dev-only-insecure-secret-change-me"


def mint_session_jwt(email: str, role: str) -> str:
    try:
        import jwt  # PyJWT
    except ImportError as exc:
        raise RuntimeError("PyJWT not installed") from exc
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(hours=settings.SESSION_TTL_HOURS)
    payload = {"sub": email.lower().strip(), "role": role, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, _secret(), algorithm=settings.JWT_ALGORITHM)


def decode_session_jwt(token: str) -> Dict[str, Any]:
    try:
        import jwt
    except ImportError as exc:
        raise RuntimeError("PyJWT not installed") from exc
    return jwt.decode(token, _secret(), algorithms=[settings.JWT_ALGORITHM])
