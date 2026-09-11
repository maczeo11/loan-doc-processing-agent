"""Google ID-token verification (google-auth; isolated in apps/api/auth per AGENTS §3)."""

import logging
from typing import Dict, Any, List
from apps.api.config import settings

logger = logging.getLogger("finscan.auth.google")


def _client_ids() -> List[str]:
    ids = []
    if settings.GOOGLE_CLIENT_ID:
        ids.append(settings.GOOGLE_CLIENT_ID.strip())
    if settings.GOOGLE_CLIENT_IDS:
        ids.extend([s.strip() for s in settings.GOOGLE_CLIENT_IDS.split(",") if s.strip()])
    return [i for i in ids if i]


def verify_google_id_token(id_token: str) -> Dict[str, Any]:
    """Verify GIS id_token; return {email, name, picture, sub}. Raises ValueError on failure."""
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
    except ImportError as exc:
        raise ValueError("google-auth not installed") from exc

    ids = _client_ids()
    if not ids:
        raise ValueError("GOOGLE_CLIENT_ID not configured")
    req = google_requests.Request()
    last_err: Exception | None = None
    for aud in ids:
        try:
            info = google_id_token.verify_oauth2_token(id_token, req, aud)
            iss = info.get("iss", "")
            if iss not in ("accounts.google.com", "https://accounts.google.com"):
                raise ValueError(f"bad issuer {iss}")
            email = (info.get("email") or "").lower().strip()
            if not email or not info.get("email_verified"):
                raise ValueError("email not verified")
            return {
                "email": email,
                "name": info.get("name") or email,
                "picture": info.get("picture"),
                "sub": info.get("sub"),
            }
        except Exception as exc:  # try next aud
            last_err = exc
            continue
    raise ValueError(f"Google token verification failed: {last_err}")
