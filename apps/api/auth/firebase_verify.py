"""
Firebase ID-token verification (google-auth; isolated in apps/api/auth per
AGENTS §3).

Deliberately does NOT use the Firebase Admin SDK, which would require a
service-account private key on the server. Firebase ID tokens are ordinary
JWTs signed by Google - google-auth's verify_firebase_token() checks the
signature against Google's public certs and validates issuer/audience using
only the public Firebase project ID, exactly like verify_google_id_token()
already does for plain Google sign-in (google_verify.py). No secret needed.

Handles tokens from ANY Firebase Auth sign-in method (Google popup,
email/password, etc.) - Firebase issues the same kind of ID token regardless
of which provider the user actually signed in with, so one verification path
covers both.
"""

import logging
from typing import Any, Dict
from apps.api.config import settings

logger = logging.getLogger("finscan.auth.firebase")


def verify_firebase_id_token(id_token: str) -> Dict[str, Any]:
    """Verify a Firebase ID token; return {email, name, picture, sub}. Raises ValueError on failure."""
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
    except ImportError as exc:
        raise ValueError("google-auth not installed") from exc

    project_id = (settings.FIREBASE_PROJECT_ID or "").strip()
    if not project_id:
        raise ValueError("FIREBASE_PROJECT_ID not configured")

    req = google_requests.Request()
    try:
        info = google_id_token.verify_firebase_token(id_token, req, audience=project_id)
    except Exception as exc:
        raise ValueError(f"Firebase token verification failed: {exc}") from exc

    expected_iss = f"https://securetoken.google.com/{project_id}"
    if info.get("iss") != expected_iss:
        raise ValueError(f"bad issuer {info.get('iss')}")

    email = (info.get("email") or "").lower().strip()
    if not email or not info.get("email_verified", False):
        # Email/password sign-up defaults to unverified until the user clicks
        # a confirmation link - accept it for this internal allowlisted tool
        # rather than force email verification flows for a hackathon demo,
        # but still require SOME email claim to exist.
        if not email:
            raise ValueError("no email claim in token")

    return {
        "email": email,
        "name": info.get("name") or email,
        "picture": info.get("picture"),
        "sub": info.get("sub") or info.get("user_id"),
    }
