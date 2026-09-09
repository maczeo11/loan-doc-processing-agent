"""
API-owned storage dependency factory for FinScan AI.

Instantiates and provides the configured StoragePort adapter implementation
(LocalFileSystemStorage or S3Storage) from adapters.storage without duplicate logic.
"""

import logging
from adapters.storage.base import StoragePort
from adapters.storage.local_fs import LocalFileSystemStorage
from adapters.storage.s3 import S3Storage
from apps.api.config import settings

logger = logging.getLogger("finscan.storage")


def get_storage() -> StoragePort:
    """
    FastAPI dependency yielding the configured StoragePort implementation.
    Selects adapter based on settings.STORAGE_BACKEND ('local' or 's3').
    """
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage(bucket_name=settings.S3_BUCKET, region=settings.AWS_REGION)
    return LocalFileSystemStorage(base_dir=settings.STORAGE_BASE_DIR)
