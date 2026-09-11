"""Auth schemas (Pydantic v2)."""

from typing import Optional
from pydantic import BaseModel, Field


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., min_length=10, max_length=8192)


class SessionUser(BaseModel):
    email: str
    name: Optional[str] = None
    picture_url: Optional[str] = None
    role: str = "SENIOR_UNDERWRITER"


class GoogleLoginResponse(BaseModel):
    user: SessionUser
    session_jwt: str


class AuthMeResponse(SessionUser):
    pass
