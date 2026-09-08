"""
Unit tests for document upload validation, filename sanitization, format verification,
storage dependency factory alignment, and canonical build_storage_key helper.
"""

import inspect
import pytest
from fastapi import HTTPException

import apps.api.routes.documents as doc_module
from apps.api.config import settings
from apps.api.storage import get_storage
import apps.api.storage as api_storage
from adapters.storage.base import StoragePort, build_storage_key
from adapters.storage.local_fs import LocalFileSystemStorage
from adapters.storage.s3 import S3Storage
from apps.api.routes.documents import sanitize_filename, validate_file_signature


def test_sanitize_filename_valid_cases():
    """Verifies valid filenames are accepted and cleaned."""
    assert sanitize_filename("payslip_june.pdf") == "payslip_june.pdf"
    assert sanitize_filename("bank-statement.2024.pdf") == "bank-statement.2024.pdf"
    assert sanitize_filename("passport_scan.jpg") == "passport_scan.jpg"
    assert sanitize_filename("id_card.png") == "id_card.png"


def test_sanitize_filename_path_traversal_rejected():
    """Verifies directory traversal sequences are strictly rejected."""
    with pytest.raises(HTTPException) as exc1:
        sanitize_filename("../../etc/passwd.pdf")
    assert exc1.value.status_code == 400

    with pytest.raises(HTTPException) as exc2:
        sanitize_filename("..\\..\\windows\\system32\\cmd.pdf")
    assert exc2.value.status_code == 400

    with pytest.raises(HTTPException) as exc3:
        sanitize_filename("../secret.pdf")
    assert exc3.value.status_code == 400


def test_sanitize_filename_empty_or_whitespace_rejected():
    """Verifies empty or whitespace filenames are rejected."""
    with pytest.raises(HTTPException) as exc1:
        sanitize_filename("")
    assert exc1.value.status_code == 400

    with pytest.raises(HTTPException) as exc2:
        sanitize_filename("   ")
    assert exc2.value.status_code == 400

    with pytest.raises(HTTPException) as exc3:
        sanitize_filename(None)
    assert exc3.value.status_code == 400


def test_sanitize_filename_unsupported_extension_rejected():
    """Verifies disallowed extensions (.exe, .zip, .sh, .txt) are rejected."""
    disallowed = ["payload.exe", "archive.zip", "script.sh", "notes.txt", "document.docx"]
    for name in disallowed:
        with pytest.raises(HTTPException) as exc:
            sanitize_filename(name)
        assert exc.value.status_code == 400
        assert "unsupported file extension" in exc.value.detail.lower()


def test_validate_file_signature_valid_formats():
    """Verifies magic bytes for allowed formats pass verification."""
    # PDF
    validate_file_signature(b"%PDF-1.4 header contents")
    # JPEG
    validate_file_signature(b"\xff\xd8\xff\xe0\x00\x10JFIF")
    # PNG
    validate_file_signature(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    # TIFF (Little-endian & Big-endian)
    validate_file_signature(b"II*\x00\x08\x00\x00\x00")
    validate_file_signature(b"MM\x00*\x00\x00\x00\x08")


def test_validate_file_signature_invalid_formats():
    """Verifies corrupted or spoofed content headers are rejected."""
    with pytest.raises(HTTPException) as exc1:
        validate_file_signature(b"MZ\x90\x00executable bytes")  # Windows executable
    assert exc1.value.status_code == 400
    assert "magic bytes" in exc1.value.detail.lower()

    with pytest.raises(HTTPException) as exc2:
        validate_file_signature(b"PK\x03\x04zip archive bytes")  # Zip archive
    assert exc2.value.status_code == 400

    with pytest.raises(HTTPException) as exc3:
        validate_file_signature(b"Plain text masquerading as pdf")
    assert exc3.value.status_code == 400

    with pytest.raises(HTTPException) as exc4:
        validate_file_signature(b"")  # Empty
    assert exc4.value.status_code == 400


def test_storage_dependency_returns_local_adapter(monkeypatch):
    """Verifies get_storage returns LocalFileSystemStorage when STORAGE_BACKEND is 'local'."""
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    storage = get_storage()
    assert isinstance(storage, LocalFileSystemStorage)
    from pathlib import Path
    assert Path(storage.base_dir) == Path(settings.STORAGE_BASE_DIR).resolve()


def test_storage_dependency_returns_s3_adapter(monkeypatch):
    """Verifies get_storage returns S3Storage when STORAGE_BACKEND is 's3'."""
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    storage = get_storage()
    assert isinstance(storage, S3Storage)
    assert storage.bucket_name == settings.S3_BUCKET
    assert storage.region == settings.AWS_REGION


def test_no_duplicate_storage_port_in_apps_api():
    """
    Verifies that apps/api/storage.py does not define its own StoragePort
    or duplicate adapter implementations; only thin dependency wiring.
    """
    locally_defined = [
        cls for name, cls in inspect.getmembers(api_storage, inspect.isclass)
        if cls.__module__ == "apps.api.storage"
    ]
    assert len(locally_defined) == 0, f"Found unexpected classes defined in apps.api.storage: {locally_defined}"
    assert not hasattr(api_storage, "LocalDiskStorageService")


def test_build_storage_key_exact_flattened_format():
    """
    Verifies build_storage_key produces canonical dossiers/{app_id}/{doc_id}_{filename} format.
    """
    key = build_storage_key("APP-25195", "DOC-123", "salary_slip.pdf")
    assert key == "dossiers/APP-25195/DOC-123_salary_slip.pdf"


def test_build_storage_key_sanitizes_filenames():
    """
    Verifies build_storage_key strips path traversal sequences and cleans special characters.
    """
    key1 = build_storage_key("APP-100", "DOC-001", "../../secret/my statement (final).pdf")
    assert key1 == "dossiers/APP-100/DOC-001_my_statement__final_.pdf"

    key2 = build_storage_key("APP-100", "DOC-002", "..\\..\\windows\\sys.pdf")
    assert key2 == "dossiers/APP-100/DOC-002_sys.pdf"


def test_build_storage_key_same_filename_produces_distinct_keys():
    """
    Verifies uploading the same filename twice yields distinct keys due to differing document IDs.
    """
    key1 = build_storage_key("APP-500", "DOC-AAA", "payslip.pdf")
    key2 = build_storage_key("APP-500", "DOC-BBB", "payslip.pdf")
    assert key1 != key2
    assert key1 == "dossiers/APP-500/DOC-AAA_payslip.pdf"
    assert key2 == "dossiers/APP-500/DOC-BBB_payslip.pdf"


def test_route_uses_build_storage_key_symbol():
    """
    Verifies the documents route module imports and exposes build_storage_key.
    """
    assert hasattr(doc_module, "build_storage_key")
    assert callable(doc_module.build_storage_key)