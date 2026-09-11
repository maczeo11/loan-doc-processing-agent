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
   treated as untrusted (deleted when possible). On success the document is
   registered (DocumentModel + application state_json) so the dossier can be
   processed, exactly as with the proxied POST /documents path.

Owned by Member 2 (Bhanu Teja). Additive: does not modify documents.py.
"""

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field, ValidationError

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
    filename: str
    storage_key: str
    sha256: str
    size_bytes: int
    verified_via: str
    registered: bool


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


async def _parse_complete_request(request: Request) -> CompleteRequest:
    """
    Read CompleteRequest from either a JSON body (S3 mode) or multipart form
    fields (local api_relay mode, where the bytes ride along as `file`).

    FastAPI cannot bind a Pydantic body model and multipart fields on the same
    endpoint: declaring `payload: CompleteRequest` next to `file: UploadFile`
    made the relay path impossible to call, since a multipart request always
    failed body validation with "payload: Field required".
    """
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("multipart/form-data") or content_type.startswith(
        "application/x-www-form-urlencoded"
    ):
        form = await request.form()
        raw: Dict[str, Any] = {
            key: value for key, value in form.items() if not hasattr(value, "filename")
        }
    else:
        try:
            raw = await request.json()
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request body must be JSON or multipart form")
    try:
        return CompleteRequest.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.errors())


@router.post(
    "/{id}/uploads/complete",
    response_model=CompleteResponse,
    dependencies=[Depends(rate_limit_upload)],
)
async def complete_upload(
    id: str,
    request: Request,
    storage: StoragePort = Depends(get_storage),
    session=Depends(get_db),
    file: Optional[UploadFile] = File(default=None),
    ticket: Optional[str] = Form(default=None),
) -> CompleteResponse:
    """
    Verify a direct upload by recomputing SHA-256 server-side.

    - S3 mode: JSON body; object already in bucket, verify checksum/metadata only.
    - Local api_relay mode: multipart `file` + `ticket` carry the bytes; bytes are
      stored first, then verified, and deleted on mismatch.

    On success the document is registered so the dossier is processable.
    """
    import asyncio

    from sqlalchemy import select

    from apps.api.db.models import ApplicationModel

    payload = await _parse_complete_request(request)

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

    verified_sha = str(receipt.get("sha256", payload.sha256_hex.lower()))
    verified_size = int(receipt.get("size_bytes", payload.size_bytes))

    # Register the document so a presigned upload produces the same durable
    # state as POST /documents. Without this the bytes landed in storage but no
    # DocumentModel row existed, so the dossier could never be processed — the
    # direct-upload path was effectively a no-op.
    registered = await _register_document(
        session=session,
        application_id=id,
        document_id=payload.document_id,
        storage_key=storage_key,
        sha256=verified_sha,
        size_bytes=verified_size,
    )

    return CompleteResponse(
        document_id=payload.document_id,
        application_id=id,
        filename=os.path.basename(storage_key),
        storage_key=storage_key,
        sha256=verified_sha,
        size_bytes=verified_size,
        verified_via=str(receipt.get("verified_via", "rehash")),
        registered=registered,
    )


async def _register_document(
    session,
    application_id: str,
    document_id: str,
    storage_key: str,
    sha256: str,
    size_bytes: int,
) -> bool:
    """
    Persist DocumentModel + application state_json for a verified direct upload.

    Idempotent: re-completing the same document_id updates the existing row
    rather than raising, because at-least-once clients may retry.
    """
    from sqlalchemy import select

    from apps.api.db.models import ApplicationModel, DocumentModel, utc_now

    filename = os.path.basename(storage_key)
    now = utc_now()

    existing = (
        await session.execute(select(DocumentModel).where(DocumentModel.id == document_id))
    ).scalar_one_or_none()

    if existing is not None:
        if existing.application_id != application_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Document '{document_id}' already belongs to another application",
            )
        existing.storage_uri = storage_key
        existing.sha256 = sha256
        existing.size_bytes = size_bytes
    else:
        session.add(
            DocumentModel(
                id=document_id,
                application_id=application_id,
                filename=filename,
                storage_uri=storage_key,
                doc_type=None,
                sha256=sha256,
                size_bytes=size_bytes,
                created_at=now,
            )
        )

    app_model = (
        await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == application_id)
        )
    ).scalar_one_or_none()
    if app_model is not None:
        state = dict(app_model.state_json or {})
        doc_ids = list(state.get("document_ids", []))
        if document_id not in doc_ids:
            doc_ids.append(document_id)
        state["document_ids"] = doc_ids

        manifest = dict(state.get("document_manifest", {}))
        manifest[document_id] = storage_key
        state["document_manifest"] = manifest

        filenames = dict(state.get("document_filenames", {}))
        filenames[document_id] = filename
        state["document_filenames"] = filenames

        app_model.state_json = state
        app_model.updated_at = now

    try:
        await session.commit()
    except Exception as db_err:  # noqa: BLE001 - surfaced to the caller
        await session.rollback()
        logger.error(
            f"Failed to register direct upload '{document_id}' for '{application_id}': {db_err}",
            exc_info=True,
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Upload verified but document registration failed",
        )
    return True
