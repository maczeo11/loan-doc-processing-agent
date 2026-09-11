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
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_IDS: str = ""
    JWT_SECRET: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    SESSION_TTL_HOURS: int = 12
    AUTHORIZED_EMAILS: str = ""
    AUTHORIZED_DOMAINS: str = ""

    # OpenCode API
    OPENCODE_API_KEY: str = ""

    # Rate limits & spend guards
    MAX_ACTIVE_JOBS_PER_USER: int = 2
    MAX_SUBMISSIONS_PER_MIN: int = 5
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
