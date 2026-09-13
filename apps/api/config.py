"""
API configuration and settings.
"""

from typing import List, Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings


class AsyncCompatibleDsn(str):
    """
    Dual-driver compatible connection string.
    Acts as postgresql+asyncpg:// for SQLAlchemy asyncpg engine,
    and seamlessly encodes and identifies as postgresql:// for psycopg / libpq drivers.
    """
    def encode(self, encoding="utf-8", errors="strict"):
        clean = self.replace("postgresql+asyncpg://", "postgresql://")
        return clean.encode(encoding, errors)

    def startswith(self, prefix, *args, **kwargs):
        if prefix in ("postgresql://", "postgres://", ("postgresql://", "postgres://")):
            return True
        return super().startswith(prefix, *args, **kwargs)


class Settings(BaseSettings):
    ENVIRONMENT: Literal["local", "cloud", "production"] = "local"
    RELEASE_VERSION: str = "1.0.0"
    GIT_SHA: str = "unknown"
    BUILD_TIMESTAMP: str = "unknown"
    API_PORT: int = 8000
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/finscan"
    # Migrations run DDL, which does not tolerate PgBouncer's transaction
    # pooling well (a schema change must see its own prior statements on the
    # SAME backend connection). Empty means "use DATABASE_URL as-is" (no
    # PgBouncer in front, e.g. local dev); set this to the direct
    # :5432 URL once DATABASE_URL points at PgBouncer's :6432 in production.
    ALEMBIC_DATABASE_URL: str = ""
    DATABASE_ECHO: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CONNECT_TIMEOUT_SECONDS: float = 2.0

    # Adapter selections
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_BASE_DIR: str = "data/storage"
    QUEUE_BACKEND: Literal["postgres", "sqs"] = "postgres"
    LLM_BACKEND: Literal["opencode", "qwen_offline"] = "opencode"

    # S3 / SQS config
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "finscan-dossiers-dev"
    SQS_QUEUE_URL: str = ""
    SQS_DLQ_URL: str = ""

    # Auth (Google allowlisted; mock for local/viva)
    AUTH_MODE: Literal["mock", "google", "required"] = "mock"
    # Whether this deployment is actually served over HTTPS. The session
    # cookie's Secure flag must match reality: a Secure cookie set over plain
    # HTTP is silently dropped by every browser, breaking login right after
    # it "succeeds" (the very next authenticated request comes back 401).
    # Previously inferred from ENVIRONMENT=="production", which broke this
    # exact deployment (production, but HTTP-only, no domain/TLS yet).
    # Flip to true once real TLS (Caddy auto-HTTPS with a real domain) is live.
    TLS_ENABLED: bool = False
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_IDS: str = ""
    # Firebase Auth (apps/api/auth/firebase_verify.py): when set, /auth/google
    # verifies incoming tokens as Firebase ID tokens instead of plain Google
    # ID tokens - covers both Google-via-Firebase and email/password sign-in,
    # since Firebase issues the same token shape for either. No service
    # account/private key needed - see that module's docstring.
    FIREBASE_PROJECT_ID: str = ""
    JWT_SECRET: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    SESSION_TTL_HOURS: int = 12
    AUTHORIZED_EMAILS: str = ""
    AUTHORIZED_DOMAINS: str = ""

    # OpenCode API
    OPENCODE_API_KEY: str = ""

    # Experimental: read-only tool-calling agent for the underwriter Q&A endpoint
    # (apps/api/agent.py). Off by default; the endpoint falls back to the
    # existing single-shot LLM path on any failure regardless of this flag.
    AGENTIC_QA_ENABLED: bool = False

    # How long an /applications/{id}/questions answer is served from Redis
    # before falling back to a fresh retrieval+synthesis pass. Keyed on the
    # dossier's updated_at too (see review.py:_qa_cache_key), so a real state
    # change invalidates the cache immediately regardless of this TTL - this
    # only bounds how long an answer to an UNCHANGED dossier can be reused.
    QA_CACHE_TTL_SECONDS: int = 900

    # asyncpg's per-connection prepared-statement cache is incompatible with
    # PgBouncer's transaction pooling mode (a "prepared statement does not
    # exist" error surfaces once a session's underlying backend connection
    # rotates mid-session). 0 disables it. Safe to leave at 0 even against a
    # direct (non-pooled) Postgres connection - it costs a little re-parse
    # overhead per query, not correctness - so this defaults to 0 unconditionally
    # rather than requiring every deployment to remember to set it.
    DATABASE_STATEMENT_CACHE_SIZE: int = 0

    # Rate limits & spend guards
    MAX_ACTIVE_JOBS_PER_USER: int = 2
    MAX_SUBMISSIONS_PER_MIN: int = 30
    MAX_STATUS_POLLS_PER_MIN: int = 30
    SPEND_GUARD_RESERVATION_TTL_SECONDS: int = 900  # 15 minutes safety TTL
    MAX_FILE_SIZE_MB: int = 10
    MAX_PAGES_PER_APP: int = 30

    # Document upload validation
    ALLOWED_CONTENT_TYPES: List[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
    ]
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".tiff"]

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def wrap_database_url(cls, v: str) -> str:
        if v and v.startswith("postgresql+asyncpg://"):
            return AsyncCompatibleDsn(v)
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
