"""Auth routes: POST /auth/google, GET /auth/me, POST /auth/logout."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.config import settings
from apps.api.db.models import UserModel
from apps.api.db.session import get_db
from apps.api.auth.schemas import GoogleLoginRequest, GoogleLoginResponse, SessionUser, AuthMeResponse
from apps.api.auth.google_verify import verify_google_id_token
from apps.api.auth.allowlist import get_or_seed_user
from apps.api.auth.session import mint_session_jwt
from apps.api.auth.deps import get_current_user

logger = logging.getLogger("finscan.auth.routes")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=GoogleLoginResponse)
async def google_login(payload: GoogleLoginRequest, response: Response, session: AsyncSession = Depends(get_db)):
    if settings.AUTH_MODE == "mock":
        # Mock passthrough for local/viva (no Google verification).
        user = SessionUser(email="akshaya.underwriting@finscan.internal", name="Akshaya S.", role="SENIOR_UNDERWRITER")
        token = mint_session_jwt(user.email, user.role)
        _set_cookie(response, token)
        return GoogleLoginResponse(user=user, session_jwt=token)
    try:
        claims = verify_google_id_token(payload.id_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Google verification failed: {exc}")
    user_row = await get_or_seed_user(
        session,
        email=claims["email"],
        name=claims.get("name"),
        picture_url=claims.get("picture"),
        google_sub=claims.get("sub"),
    )
    user_row.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    if not bool(user_row.authorized):
        # Generic denial (don't leak allowlist).
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not authorized for FinScan")
    token = mint_session_jwt(user_row.email, user_row.role)
    _set_cookie(response, token)
    return GoogleLoginResponse(
        user=SessionUser(email=user_row.email, name=user_row.name, picture_url=user_row.picture_url, role=user_row.role),
        session_jwt=token,
    )


@router.get("/me", response_model=AuthMeResponse)
async def auth_me(user: UserModel = Depends(get_current_user)):
    return AuthMeResponse(email=user.email, name=user.name, picture_url=user.picture_url, role=user.role)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("finscan_session")
    return {"status": "logged_out"}


def _set_cookie(response: Response, token: str) -> None:
    secure = settings.ENVIRONMENT in ("cloud", "production")
    response.set_cookie(
        "finscan_session",
        token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.SESSION_TTL_HOURS * 3600,
        path="/",
    )
