"""
Unit tests for LocalFileSystemStorage and S3Storage adapters.
Owned by Member 2 (Bhanu Teja).

Verifies:
- LocalFileSystemStorage: atomic writes, read, directory traversal protection, SHA-256, delete.
- S3Storage: boto3 put_object, upload_fileobj, get_object, presigned URLs, head/delete.
"""

import io
import hashlib
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from adapters.storage.local_fs import LocalFileSystemStorage
from adapters.storage.s3 import S3Storage


# =====================================================================
# LocalFileSystemStorage Tests
# =====================================================================

def test_local_storage_put_and_get_bytes(tmp_path: Path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))
    content = b"PDF dummy content for unit test"

    uri = storage.put("dossiers/doc1.pdf", content)

    assert uri.startswith("file://")
    assert uri.endswith("dossiers/doc1.pdf")
    retrieved = storage.get("dossiers/doc1.pdf")
    assert retrieved == content


def test_local_storage_put_file_stream(tmp_path: Path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))
    content = b"BinaryIO stream content"
    stream = io.BytesIO(content)

    uri = storage.put("subfolder/stream_doc.pdf", stream)

    assert uri.startswith("file://")
    assert storage.get("subfolder/stream_doc.pdf") == content


def test_local_storage_exists_and_delete(tmp_path: Path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))
    storage.put("sample.pdf", b"test")

    assert storage.exists("sample.pdf") is True
    assert storage.delete("sample.pdf") is True
    assert storage.exists("sample.pdf") is False
    assert storage.delete("sample.pdf") is False


def test_local_storage_compute_sha256(tmp_path: Path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))
    content = b"Exact integrity test payload"
    expected_hash = hashlib.sha256(content).hexdigest()

    storage.put("hash_test.pdf", content)
    computed_hash = storage.compute_sha256("hash_test.pdf")

    assert computed_hash == expected_hash


def test_local_storage_get_signed_url():
    storage = LocalFileSystemStorage(base_dir="data/storage", base_url="http://localhost:8000")
    url = storage.get_signed_url("apps/app123/payslip.pdf")
    assert url == "http://localhost:8000/files/apps/app123/payslip.pdf"


def test_local_storage_directory_traversal_prevention(tmp_path: Path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))
    with pytest.raises(ValueError, match="Directory traversal"):
        storage.put("../../etc/passwd", b"evil")


def test_local_storage_get_nonexistent_raises(tmp_path: Path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        storage.get("nonexistent_file.pdf")


# =====================================================================
# S3Storage Tests
# =====================================================================

def test_s3_storage_put_bytes():
    mock_s3 = MagicMock()
    storage = S3Storage(bucket_name="finscan-dossiers", region="us-east-1", s3_client=mock_s3)
    content = b"S3 raw binary upload"

    uri = storage.put("dossiers/apps/app01/id.pdf", content)

    assert uri == "s3://finscan-dossiers/dossiers/apps/app01/id.pdf"
    mock_s3.put_object.assert_called_once_with(
        Bucket="finscan-dossiers",
        Key="dossiers/apps/app01/id.pdf",
        Body=content,
        ContentType="application/pdf",
        ServerSideEncryption="AES256",
    )


def test_s3_storage_put_stream():
    mock_s3 = MagicMock()
    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock_s3)
    stream = io.BytesIO(b"Stream data for S3")

    uri = storage.put("dossiers/apps/app01/payslip.pdf", stream)

    assert uri == "s3://finscan-dossiers/dossiers/apps/app01/payslip.pdf"
    mock_s3.upload_fileobj.assert_called_once_with(
        stream,
        "finscan-dossiers",
        "dossiers/apps/app01/payslip.pdf",
        ExtraArgs={"ContentType": "application/pdf", "ServerSideEncryption": "AES256"},
    )


def test_s3_storage_get():
    mock_s3 = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b"Retrieved from S3"
    mock_s3.get_object.return_value = {"Body": mock_body}

    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock_s3)
    data = storage.get("apps/app01/tax.pdf")

    assert data == b"Retrieved from S3"
    mock_s3.get_object.assert_called_once_with(
        Bucket="finscan-dossiers",
        Key="apps/app01/tax.pdf",
    )


def test_s3_storage_get_signed_url():
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://signed.s3.amazonaws.com/doc.pdf?token=123"

    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock_s3)
    url = storage.get_signed_url("dossiers/APP-25195/DOC-00001_bank.pdf", expires_in=1800)

    assert url == "https://signed.s3.amazonaws.com/doc.pdf?token=123"
    mock_s3.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "finscan-dossiers", "Key": "dossiers/APP-25195/DOC-00001_bank.pdf"},
        ExpiresIn=1800,
    )


def test_s3_storage_exists_and_delete():
    mock_s3 = MagicMock()
    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock_s3)

    # Exists: True
    mock_s3.head_object.return_value = {}
    assert storage.exists("doc.pdf") is True

    # Delete
    assert storage.delete("doc.pdf") is True
    mock_s3.delete_object.assert_called_once_with(Bucket="finscan-dossiers", Key="doc.pdf")


# =====================================================================
# Canonical Storage Key & Sanitization Tests
# =====================================================================

def test_sanitize_filename():
    from adapters.storage.base import sanitize_filename

    assert sanitize_filename("simple_salary.pdf") == "simple_salary.pdf"
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("my payslip (March 2024) #1!.pdf") == "my_payslip__March_2024___1_.pdf"
    assert sanitize_filename("") == "document.pdf"


def test_build_storage_key_canonical_format():
    from adapters.storage.base import build_storage_key

    app_id = "APP-25195"
    doc_id = "DOC-99182"
    filename = "march payslip (verified).pdf"

    key = build_storage_key(app_id, doc_id, filename)

    assert key == "dossiers/APP-25195/DOC-99182_march_payslip__verified_.pdf"
    assert key.startswith("dossiers/APP-25195/")
    assert f"{doc_id}_" in key


def test_storage_package_exports():
    from adapters.storage import (
        StoragePort,
        LocalFileSystemStorage,
        S3Storage,
        build_storage_key,
        sanitize_filename,
    )
    assert callable(build_storage_key)
    assert callable(sanitize_filename)
    assert StoragePort is not None
    assert LocalFileSystemStorage is not None
    assert S3Storage is not None
