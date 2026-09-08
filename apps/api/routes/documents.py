"""
Document upload and registration routes.

Endpoints:
- POST /applications/{id}/documents
"""

from fastapi import APIRouter, UploadFile, File, Form, status
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/applications", tags=["Documents"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    application_id: str
    filename: str
    sha256: str
    size_bytes: int


@router.post("/{id}/documents", status_code=status.HTTP_201_CREATED, response_model=DocumentUploadResponse)
async def upload_document(
    id: str,
    file: UploadFile = File(...),
    doc_type_hint: Optional[str] = Form(None)
):
    """
    Upload a document for a specific application.
    Stores file in configured storage adapter (Local FS or S3) and returns metadata.
    """
    # Stub: Manjunath & Jeevan to implement file saving and hash verification
    return DocumentUploadResponse(
        document_id="DOC-PENDING",
        application_id=id,
        filename=file.filename or "unknown",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        size_bytes=0
    )
