"""
Presigned direct-upload routes (browser -> storage without proxying bytes).

Flow:
1. POST /applications/{id}/uploads/presign {document_id, filename, content_type,
   sha256_hex, size_bytes} -> {mode, upload_url|ticket, fields, storage_key, expires_in}
   - S3 backend: presigned POST bound to exact key + SHA-256 checksum + SSE + 10MB ceiling.
   - Local backend: single-use HMAC ticket; bytes relay via /uploads/complete.
2. Browser uploads bytes direct to S3 (or relays to /uploads/complete locally).
3. POST /applications/{id}/uploads/complete {document_id, storage_key, sha256_hex,
   size_bytes[, ticket]} -> server recomputes SHA-256; mismatch -> 422 + object
   treated as untrusted (deleted when possible). Returns a verified receipt that
   Balaji's document-registration flow can persist.

Owned by Member 2 (Bhanu Teja). Additive: does not modify documents.py.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from adapters.storage.base import (
    StoragePort,
    StorageTamperError,
    build_storage_key,
    is_valid_sha256_hex,
    validate_storage_key,
)
from apps.api.config import settings
from apps.api.db.session import get_db
from apps.api.middleware.rate_limit import rate_limit_upload
from apps.api.storage import get_storage

logger = logging.getLogger("finscan.uploads")

router = APIRouter(prefix="/applications", tags=["Presigned Uploads"])

ALLOWED_UPLOAD_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}


class PresignRequest(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=64)
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/pdf", max_length=64)
    sha256_hex: str = Field(..., min_length=64, max_length=64)
    size_bytes: int = Field(..., gt=0)


class PresignResponse(BaseModel):
    mode: str
    storage_key: str
    document_id: str
    upload_url: Optional[str] = None
    fields: Dict[str, Any] = {}
    ticket: Optional[str] = None
    expires_in: int
    max_bytes: int


class CompleteRequest(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=64)
    storage_key: str = Field(..., min_length=1, max_length=512)
    sha256_hex: str = Field(..., min_length=64, max_length=64)
    size_bytes: int = Field(..., gt=0)
    ticket: Optional[str] = None


class CompleteResponse(BaseModel):
    document_id: str
    application_id: str
    storage_key: str
    sha256: str
    size_bytes: int
    verified_via: str


def _max_upload_bytes() -> int:
    return int(settings.MAX_FILE_SIZE_MB) * 1024 * 1024


@router.post(
    "/{id}/uploads/presign",
    response_model=PresignResponse,
    dependencies=[Depends(rate_limit_upload)],
)
async def presign_upload(
    id: str,
    payload: PresignRequest,
    storage: StoragePort = Depends(get_storage),
    session=Depends(get_db),
) -> PresignResponse:
    """Mint a short-lived, key- and checksum-bound direct-upload grant."""
    from sqlalchemy import select

    from apps.api.db.models import ApplicationModel

    result = await session.execute(select(ApplicationModel).where(ApplicationModel.id == id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Application '{id}' not found")

    if payload.content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported content type")
    if not is_valid_sha256_hex(payload.sha256_hex):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "sha256_hex must be 64-char hex")
    max_bytes = _max_upload_bytes()
    if payload.size_bytes > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB",
        )

    try:
        storage_key = build_storage_key(id, payload.document_id, payload.filename)
        validate_storage_key(storage_key, application_id=id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    try:
        grant = storage.generate_upload_url(
            storage_key,
            payload.sha256_hex.lower(),
            content_type=payload.content_type,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"Presign failed for '{storage_key}': {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to mint upload grant")

    mode = str(grant.get("mode", "s3_post"))
    if mode == "api_relay":
        return PresignResponse(
            mode=mode,
            storage_key=storage_key,
            document_id=payload.document_id,
            ticket=str(grant.get("ticket", "")),
            expires_in=int(grant.get("expires_in", 900)),
            max_bytes=max_bytes,
        )
    return PresignResponse(
        mode="s3_post",
        storage_key=storage_key,
        document_id=payload.document_id,
        upload_url=str(grant.get("url", "")),
        fields=dict(grant.get("fields", {})),
        expires_in=int(grant.get("expires_in", 900)),
        max_bytes=int(grant.get("max_bytes", max_bytes)),
    )


@router.post(
    "/{id}/uploads/complete",
    response_model=CompleteResponse,
    dependencies=[Depends(rate_limit_upload)],
)
async def complete_upload(
    id: str,
    payload: CompleteRequest,
    storage: StoragePort = Depends(get_storage),
    session=Depends(get_db),
    file: Optional[UploadFile] = File(default=None),
    ticket: Optional[str] = Form(default=None),
) -> CompleteResponse:
    """
    Verify a direct upload by recomputing SHA-256 server-side.

    - S3 mode: object already in bucket; verify checksum/metadata only.
    - Local api_relay mode: multipart `file` + `ticket` carry the bytes; bytes are
      stored first, then verified, and deleted on mismatch.
    """
    import asyncio

    from sqlalchemy import select

    from apps.api.db.models import ApplicationModel

    result = await session.execute(select(ApplicationModel).where(ApplicationModel.id == id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Application '{id}' not found")

    if not is_valid_sha256_hex(payload.sha256_hex):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "sha256_hex must be 64-char hex")
    try:
        storage_key = validate_storage_key(payload.storage_key, application_id=id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    stored_here = False
    if file is not None:
        # Local relay path: ticket authorizes the byte relay, then verify.
        presented = ticket or payload.ticket or ""
        verifier = getattr(storage, "verify_upload_ticket", None)
        if verifier is None or not verifier(presented, storage_key, payload.sha256_hex.lower()):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid or expired upload ticket")
        content = await file.read()
        if not content:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")
        if len(content) > _max_upload_bytes():
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB",
            )
        try:
            await asyncio.to_thread(storage.put, storage_key, content)
            stored_here = True
        except Exception as e:
            logger.error(f"Relay store failed for '{storage_key}': {e}", exc_info=True)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to store upload")

    try:
        receipt = await asyncio.to_thread(
            storage.verify_integrity, storage_key, payload.sha256_hex.lower()
        )
    except StorageTamperError as e:
        logger.warning(f"Tamper detected on '{storage_key}': {e}")
        if stored_here:
            deleter = getattr(storage, "delete", None)
            if callable(deleter):
                try:
                    await asyncio.to_thread(deleter, storage_key)
                except Exception as del_err:  # noqa: BLE001 - best-effort quarantine
                    logger.warning(f"Failed to quarantine tampered object '{storage_key}': {del_err}")
            else:
                logger.warning(f"No delete() on storage; tampered object '{storage_key}' needs manual purge")
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Integrity check failed: {e}")
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"Integrity verification failed for '{storage_key}': {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Integrity verification failed")

    return CompleteResponse(
        document_id=payload.document_id,
        application_id=id,
        storage_key=storage_key,
        sha256=str(receipt.get("sha256", payload.sha256_hex.lower())),
        size_bytes=int(receipt.get("size_bytes", payload.size_bytes)),
        verified_via=str(receipt.get("verified_via", "rehash")),
    )
