"""Allowlist: DB users.authorized is source of truth; env seeds first login."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.config import settings
from apps.api.db.models import UserModel


def _seed_emails() -> set:
    out = set()
    for chunk in (settings.AUTHORIZED_EMAILS or "").split(","):
        e = chunk.strip().lower()
        if e:
            out.add(e)
    return out


def _seed_domains() -> set:
    out = set()
    for chunk in (settings.AUTHORIZED_DOMAINS or "").split(","):
        d = chunk.strip().lower().lstrip("@")
        if d:
            out.add(d)
    return out


def seed_authorized(email: str) -> bool:
    email = email.lower().strip()
    if email in _seed_emails():
        return True
    if "@" in email:
        domain = email.split("@", 1)[1]
        if domain in _seed_domains():
            return True
    return False


async def get_or_seed_user(
    session: AsyncSession,
    email: str,
    name: Optional[str] = None,
    picture_url: Optional[str] = None,
    google_sub: Optional[str] = None,
) -> UserModel:
    email = email.lower().strip()
    res = await session.execute(select(UserModel).where(UserModel.email == email))
    user = res.scalar_one_or_none()
    if user is None:
        user = UserModel(
            email=email,
            name=name,
            picture_url=picture_url,
            role="SENIOR_UNDERWRITER",
            authorized=seed_authorized(email),
            google_sub=google_sub,
        )
        session.add(user)
        await session.flush()
    else:
        updated = False
        if name and user.name != name:
            user.name = name
            updated = True
        if picture_url and user.picture_url != picture_url:
            user.picture_url = picture_url
            updated = True
        if google_sub and user.google_sub != google_sub:
            user.google_sub = google_sub
            updated = True
        if updated:
            await session.flush()
    return user
