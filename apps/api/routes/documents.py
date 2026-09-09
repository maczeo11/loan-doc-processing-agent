"""
Document upload and metadata persistence routes for FinScan AI.

Enforces size/extension limits, file signature (magic bytes) validation,
bounded chunk streaming SHA-256 and size computation, StoragePort persistence,
and authoritative PostgreSQL DocumentModel/ApplicationModel state update.
"""

import os
import re
import asyncio
import hashlib
import tempfile
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.models import ApplicationModel, DocumentModel, utc_now
from apps.api.db.session import get_db
from apps.api.storage import get_storage
from apps.api.middleware.rate_limit import rate_limit_upload
from adapters.storage.base import StoragePort, build_storage_key

logger = logging.getLogger("finscan.documents")

router = APIRouter(prefix="/applications", tags=["Documents"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    application_id: str
    filename: str
    sha256: str
    size_bytes: int


def sanitize_filename(raw_filename: Optional[str]) -> str:
    """
    Sanitizes user-provided filename to prevent path traversal and unsafe characters.
    """
    if not raw_filename or not raw_filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty",
        )

    raw = raw_filename.strip()
    # Detect path traversal attempts before stripping
    if ".." in raw or "/" in raw or "\\" in raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal sequences are not permitted",
        )
    base_name = os.path.basename(raw)

    # Keep only alphanumeric, hyphens, underscores, dots
    cleaned = re.sub(r"[^a-zA-Z0-9_\.-]", "_", base_name)
    if not cleaned or cleaned.startswith("."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains no valid characters",
        )

    # Check allowed extension
    ext = os.path.splitext(cleaned)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    return cleaned


def validate_file_signature(first_chunk: bytes) -> None:
    """
    Validates file magic bytes to prevent trusting client-provided Content-Type alone.
    Supported: PDF (%PDF), JPEG (\xff\xd8\xff), PNG (\x89PNG), TIFF (II* or MM*).
    """
    if len(first_chunk) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty or too short to identify format",
        )

    is_pdf = first_chunk.startswith(b"%PDF")
    is_jpeg = first_chunk.startswith(b"\xff\xd8\xff")
    is_png = first_chunk.startswith(b"\x89PNG\r\n\x1a\n")
    is_tiff = first_chunk.startswith(b"II*\x00") or first_chunk.startswith(b"MM\x00*")

    if not (is_pdf or is_jpeg or is_png or is_tiff):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unsupported file format. Content does not match allowed magic bytes (PDF, JPEG, PNG, TIFF).",
        )


@router.post(
    "/{id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentUploadResponse,
    dependencies=[Depends(rate_limit_upload)],
)
async def upload_document(
    id: str,
    file: UploadFile = File(...),
    doc_type_hint: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    """
    Upload a document for a specific application.
    Validates file, streams in bounded chunks, calculates SHA-256 and size,
    stores through StoragePort, and persists metadata in PostgreSQL.
    """
    # 1. Verify application exists
    result = await session.execute(
        select(ApplicationModel).where(ApplicationModel.id == id)
    )
    app_model = result.scalar_one_or_none()
    if not app_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found",
        )

    # 2. Sanitize and validate filename
    sanitized_filename = sanitize_filename(file.filename)

    # 3. Generate stable document ID
    import uuid
    doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

    # 4. Stream upload in bounded chunks: compute SHA-256 and exact byte size
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    chunk_size = 65536  # 64 KB bounded streaming
    hasher = hashlib.sha256()
    total_bytes = 0
    first_chunk = True

    # Spooled temp file stays in memory under 2MB, spills to disk for larger files
    spooled_file = tempfile.SpooledTemporaryFile(max_size=2 * 1024 * 1024)

    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break

            if first_chunk:
                validate_file_signature(chunk)
                first_chunk = False

            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB",
                )

            hasher.update(chunk)
            spooled_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)",
            )

        sha256_digest = hasher.hexdigest()

        # 5. Store file through StoragePort via build_storage_key
        storage_key = build_storage_key(
            application_id=id,
            document_id=doc_id,
            filename=file.filename,
        )
        spooled_file.seek(0)

        try:
            storage_uri = await asyncio.to_thread(storage.put, storage_key, spooled_file)
        except Exception as storage_err:
            logger.error(f"StoragePort.put failed for key '{storage_key}': {storage_err}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store uploaded document content",
            )

    finally:
        spooled_file.close()

    # 6. Persist DocumentModel and update application state_json
    try:
        doc_model = DocumentModel(
            id=doc_id,
            application_id=id,
            filename=sanitized_filename,
            storage_uri=storage_uri,
            doc_type=doc_type_hint.strip() if doc_type_hint and doc_type_hint.strip() else None,
            sha256=sha256_digest,
            size_bytes=total_bytes,
            created_at=utc_now(),
        )
        session.add(doc_model)

        # Update authoritative state_json
        state = dict(app_model.state_json or {})
        doc_ids = list(state.get("document_ids", []))
        doc_ids.append(doc_id)
        state["document_ids"] = doc_ids

        manifest = dict(state.get("document_manifest", {}))
        manifest[doc_id] = storage_uri
        state["document_manifest"] = manifest

        if doc_type_hint and doc_type_hint.strip():
            classified = dict(state.get("classified_types", {}))
            classified[doc_id] = doc_type_hint.strip()
            state["classified_types"] = classified

        app_model.state_json = state
        app_model.updated_at = utc_now()

        await session.commit()

    except Exception as db_err:
        await session.rollback()
        logger.error(f"Database commit failed after storing document '{storage_key}': {db_err}", exc_info=True)

        # Attempt safe cleanup if storage adapter supports delete
        if hasattr(storage, "delete"):
            try:
                await asyncio.to_thread(storage.delete, storage_key)
            except Exception as del_err:
                logger.warning(f"Failed to cleanup orphaned object '{storage_key}': {del_err}")
        else:
            logger.warning(
                f"StoragePort protocol does not provide delete(); object '{storage_key}' remains orphaned after DB rollback."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist document metadata in database",
        )

    return DocumentUploadResponse(
        document_id=doc_id,
        application_id=id,
        filename=sanitized_filename,
        sha256=sha256_digest,
        size_bytes=total_bytes,
    )
