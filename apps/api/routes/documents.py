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

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Response
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


EXTENSION_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tiff": "image/tiff",
}


def media_type_for_filename(filename: str) -> str:
    """
    Resolve the served Content-Type from the stored extension.

    ALLOWED_EXTENSIONS admits scanned images, so serving everything as
    application/pdf made an uploaded payslip photo unrenderable in the viewer.
    """
    ext = os.path.splitext(filename or "")[1].lower()
    return EXTENSION_MEDIA_TYPES.get(ext, "application/octet-stream")


# Canonical document types the pipeline's completeness rule requires. A hint
# lands directly in `classified_types`, and the classifier will not revisit a
# document that already carries a non-unknown type — so an off-vocabulary hint
# is sticky and makes RULE-COMP-01 report a document that is present as missing.
CANONICAL_DOC_TYPES = {
    "application_form",
    "payslip",
    "bank_statement",
    "tax_acknowledgement",
    "id_card",
}

DOC_TYPE_ALIASES = {
    "tax_return": "tax_acknowledgement",
    "tax": "tax_acknowledgement",
    "itr": "tax_acknowledgement",
    "itr_v": "tax_acknowledgement",
    "form16": "tax_acknowledgement",
    "salary": "payslip",
    "payslips": "payslip",
    "bank": "bank_statement",
    "statement": "bank_statement",
    "pan": "id_card",
    "pan_card": "id_card",
    "aadhaar": "id_card",
    "kyc": "id_card",
    "identity": "id_card",
    "application": "application_form",
    "loan_application": "application_form",
}


def normalize_doc_type_hint(raw: Optional[str]) -> Optional[str]:
    """Map a client-supplied hint onto the pipeline's vocabulary, or drop it."""
    if not raw or not raw.strip():
        return None
    value = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if value in CANONICAL_DOC_TYPES:
        return value
    mapped = DOC_TYPE_ALIASES.get(value)
    if mapped:
        return mapped
    # Unrecognised: let the classifier decide rather than pinning a bad label.
    logger.info(f"Ignoring unrecognised doc_type_hint '{raw}'; deferring to classifier")
    return None


def count_pdf_pages(storage_key: str, storage: StoragePort) -> Optional[int]:
    """
    Real page count for an uploaded PDF, or None when it cannot be determined
    (a scanned image, or PyMuPDF unavailable). Returning None is deliberate:
    the UI shows nothing rather than inventing a plausible page count.
    """
    if not storage_key.lower().endswith(".pdf"):
        return 1 if os.path.splitext(storage_key)[1].lower() in EXTENSION_MEDIA_TYPES else None
    try:
        import fitz  # PyMuPDF

        raw = storage.get(storage_key)
        with fitz.open(stream=raw, filetype="pdf") as doc:
            return int(doc.page_count)
    except Exception as err:  # noqa: BLE001 - metadata only, never fails an upload
        logger.warning(f"Could not determine page count for '{storage_key}': {err}")
        return None


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

        # Tamper close-loop: re-read + verify hash immediately after put.
        try:
            await asyncio.to_thread(storage.verify_integrity, storage_key, sha256_digest)
        except Exception as tamper_err:
            logger.error(f"Integrity verification failed for '{storage_key}': {tamper_err}", exc_info=True)
            try:
                if hasattr(storage, "delete"):
                    await asyncio.to_thread(storage.delete, storage_key)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded bytes failed integrity verification (tamper guard)",
            )

    finally:
        spooled_file.close()

    # 6. Persist DocumentModel and update application state_json
    normalized_hint = normalize_doc_type_hint(doc_type_hint)
    try:
        doc_model = DocumentModel(
            id=doc_id,
            application_id=id,
            filename=sanitized_filename,
            storage_uri=storage_uri,
            doc_type=normalized_hint,
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

        # Real filename + real page count, so the reviewer's dossier index
        # describes the file that was actually uploaded rather than a
        # placeholder derived from the generated document id.
        filenames = dict(state.get("document_filenames", {}))
        filenames[doc_id] = sanitized_filename
        state["document_filenames"] = filenames

        page_count = await asyncio.to_thread(count_pdf_pages, storage_key, storage)
        if page_count is not None:
            pages = dict(state.get("document_pages", {}))
            pages[doc_id] = page_count
            state["document_pages"] = pages

        if normalized_hint:
            classified = dict(state.get("classified_types", {}))
            classified[doc_id] = normalized_hint
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


@router.get("/{id}/documents/{doc_id}")
async def get_document_content(
    id: str,
    doc_id: str,
    session: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    """
    Stream raw document PDF bytes for in-browser canvas rendering.
    """
    stmt = select(DocumentModel).where(
        DocumentModel.id == doc_id,
        DocumentModel.application_id == id,
    )
    doc_model = (await session.execute(stmt)).scalar_one_or_none()
    if not doc_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found in application '{id}'",
        )

    storage_key = build_storage_key(
        application_id=id,
        document_id=doc_id,
        filename=doc_model.filename,
    )
    try:
        data = await asyncio.to_thread(storage.get, storage_key)
    except Exception as e:
        logger.error(f"Failed to fetch document content for '{storage_key}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document content not found in storage",
        )

    # Tamper guard: hash bytes vs DB record; mismatch -> 422 (never serve corrupt
    # PII). Raised OUTSIDE the storage try/except so it cannot be swallowed and
    # re-reported as a benign 404.
    import hashlib as _hl

    actual = _hl.sha256(data).hexdigest()
    if actual != doc_model.sha256:
        logger.error(f"SHA-256 mismatch for '{storage_key}': db={doc_model.sha256} actual={actual}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document failed integrity verification (hash mismatch)",
        )

    return Response(
        content=data,
        media_type=media_type_for_filename(doc_model.filename),
        headers={
            "Content-Disposition": f'inline; filename="{doc_model.filename}"',
            "Cache-Control": "private, max-age=3600",
            "ETag": f'"{doc_model.sha256}"',
        },
    )


class ReclassifyDocumentRequest(BaseModel):
    doc_type: str


@router.patch("/{id}/documents/{doc_id}/reclassify", response_model=dict)
async def reclassify_document(
    id: str,
    doc_id: str,
    payload: ReclassifyDocumentRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    HITL Reclassification: Allows an underwriter to override or correct a document's classification.
    Updates DocumentModel.doc_type and state_json['classified_types'] + state_json['classification_metadata'].
    """
    normalized = normalize_doc_type_hint(payload.doc_type)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type '{payload.doc_type}'. Must be one of: {sorted(list(CANONICAL_DOC_TYPES))}",
        )

    stmt = select(ApplicationModel).where(ApplicationModel.id == id).with_for_update()
    app_model = (await session.execute(stmt)).scalar_one_or_none()
    if not app_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application '{id}' not found")

    doc_stmt = select(DocumentModel).where(DocumentModel.id == doc_id, DocumentModel.application_id == id)
    doc_model = (await session.execute(doc_stmt)).scalar_one_or_none()
    if not doc_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found in application '{id}'")

    old_type = doc_model.doc_type or "unknown"
    doc_model.doc_type = normalized

    state = dict(app_model.state_json or {})
    classified = dict(state.get("classified_types", {}))
    classified[doc_id] = normalized
    state["classified_types"] = classified

    meta = dict(state.get("classification_metadata", {}))
    meta[doc_id] = {
        "confidence": 1.0,
        "class_probabilities": {normalized: 1.0},
        "model_version": "human_override",
        "method": "user_override",
        "requires_human_triage": False,
    }
    state["classification_metadata"] = meta

    app_model.state_json = state
    app_model.updated_at = utc_now()

    await session.commit()
    logger.info(f"Reclassified document '{doc_id}' in application '{id}': {old_type} -> {normalized}")

    return {
        "status": "ok",
        "document_id": doc_id,
        "application_id": id,
        "old_type": old_type,
        "new_type": normalized,
    }


@router.delete("/{id}/documents/{doc_id}", response_model=dict)
async def delete_document(
    id: str,
    doc_id: str,
    session: AsyncSession = Depends(get_db),
    storage: StoragePort = Depends(get_storage),
):
    """
    Document Deletion: Allows an underwriter to remove an erroneous or accidental document from the dossier.
    Purges storage, DocumentModel, and references in state_json.
    """
    stmt = select(ApplicationModel).where(ApplicationModel.id == id).with_for_update()
    app_model = (await session.execute(stmt)).scalar_one_or_none()
    if not app_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application '{id}' not found")

    doc_stmt = select(DocumentModel).where(DocumentModel.id == doc_id, DocumentModel.application_id == id)
    doc_model = (await session.execute(doc_stmt)).scalar_one_or_none()
    if not doc_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found in application '{id}'")

    storage_key = build_storage_key(
        application_id=id,
        document_id=doc_id,
        filename=doc_model.filename,
    )

    # 1. Purge from storage if supported
    if hasattr(storage, "delete"):
        try:
            await asyncio.to_thread(storage.delete, storage_key)
        except Exception as del_err:
            logger.warning(f"Failed to delete storage object '{storage_key}': {del_err}")

    # 2. Update state_json
    state = dict(app_model.state_json or {})
    doc_ids = [d for d in state.get("document_ids", []) if d != doc_id]
    state["document_ids"] = doc_ids

    manifest = dict(state.get("document_manifest", {}))
    manifest.pop(doc_id, None)
    state["document_manifest"] = manifest

    classified = dict(state.get("classified_types", {}))
    classified.pop(doc_id, None)
    state["classified_types"] = classified

    meta = dict(state.get("classification_metadata", {}))
    meta.pop(doc_id, None)
    state["classification_metadata"] = meta

    filenames = dict(state.get("document_filenames", {}))
    filenames.pop(doc_id, None)
    state["document_filenames"] = filenames

    pages = dict(state.get("document_pages", {}))
    pages.pop(doc_id, None)
    state["document_pages"] = pages

    routes = dict(state.get("ocr_routes", {}))
    routes.pop(doc_id, None)
    state["ocr_routes"] = routes

    app_model.state_json = state
    app_model.updated_at = utc_now()

    # 3. Delete database record
    await session.delete(doc_model)
    await session.commit()

    logger.info(f"Deleted document '{doc_id}' from application '{id}'")
    return {
        "status": "ok",
        "document_id": doc_id,
        "application_id": id,
        "deleted": True,
    }

