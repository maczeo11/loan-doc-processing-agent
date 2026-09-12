"""Auth dependencies: get_current_user + require_role. Mock passthrough preserves demo/tests."""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.config import settings
from apps.api.db.models import UserModel
from apps.api.db.session import get_db
from apps.api.auth.session import decode_session_jwt

logger = logging.getLogger("finscan.auth.deps")


def _mock_user() -> UserModel:
    u = UserModel(
        email="akshaya.underwriting@finscan.internal",
        name="Akshaya S.",
        role="SENIOR_UNDERWRITER",
        authorized=True,
    )
    return u


def _bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    cookie = request.cookies.get("finscan_session")
    if cookie:
        return cookie
    return None


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db)) -> UserModel:
    # Mock mode: passthrough (demo/viva/tests green, no JWT required).
    if settings.AUTH_MODE == "mock":
        return _mock_user()
    token = _bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session")
    try:
        claims = decode_session_jwt(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    email = (claims.get("sub") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session claims")
    res = await session.execute(select(UserModel).where(UserModel.email == email))
    user = res.scalar_one_or_none()
    if user is None or not bool(user.authorized):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not authorized")
    return user


def require_role(*roles: str):
    async def _guard(user: UserModel = Depends(get_current_user)) -> UserModel:
        if roles and user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _guard


def current_user_email(request: Request, fallback: str = "user") -> str:
    """Best-effort email for rate-limit keys (verified JWT preferred, header/IP fallback).

    The client-supplied `X-User-Id` header is only ever trusted in AUTH_MODE=="mock"
    (local/demo, no real session mechanism exists to spoof). In "google"/"required"
    mode a missing/invalid/expired JWT falls back to the generic `fallback` key
    instead of an attacker-controlled header - otherwise anyone could set
    X-User-Id to bypass a per-user rate limit or spend guard by pretending to be
    a different (or nonexistent) verified user.
    """
    if settings.AUTH_MODE != "mock":
        try:
            tok = _bearer_token(request)
            if tok:
                claims = decode_session_jwt(tok)
                email = (claims.get("sub") or "").strip()
                if email:
                    return email
        except Exception:
            pass
        return fallback
    return request.headers.get("x-user-id") or fallback
