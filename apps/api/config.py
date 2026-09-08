"""
API configuration and settings.
"""

from typing import List, Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: Literal["local", "cloud"] = "local"
    API_PORT: int = 8000
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/finscan"
    DATABASE_ECHO: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"

    # Adapter selections
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_BASE_DIR: str = "data/storage"
    QUEUE_BACKEND: Literal["postgres", "sqs"] = "postgres"
    LLM_BACKEND: Literal["opencode", "qwen_offline"] = "opencode"

    # S3 / SQS config
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "finscan-dossiers-dev"
    SQS_QUEUE_URL: str = ""

    # OpenCode API
    OPENCODE_API_KEY: str = ""

    # Rate limits & spend guards
    MAX_ACTIVE_JOBS_PER_USER: int = 2
    MAX_SUBMISSIONS_PER_MIN: int = 5
    MAX_STATUS_POLLS_PER_MIN: int = 30
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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
