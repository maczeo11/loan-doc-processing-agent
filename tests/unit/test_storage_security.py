"""
Unit tests for presigned direct-upload grants and SHA-256 tamper verification.
Owned by Member 2 (Bhanu Teja).

Covers AGENTS.md 5.5: tenant-isolated keys, checksum-bound grants, fail-closed
verification, TTL clamping, and traversal rejection.
"""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from adapters.storage.base import (
    StorageTamperError,
    clamp_presigned_ttl,
    is_valid_sha256_hex,
    sha256_base64,
    sha256_bytes,
    validate_storage_key,
)
from adapters.storage.local_fs import LocalFileSystemStorage
from adapters.storage.s3 import S3Storage

VALID_KEY = "dossiers/APP-25195/DOC-99182_payslip.pdf"
PAYLOAD = b"%PDF-1.4 tamper verification fixture"
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


# -- base primitives -------------------------------------------------------

def test_validate_storage_key_accepts_canonical():
    assert validate_storage_key(VALID_KEY, application_id="APP-25195") == VALID_KEY


def test_validate_storage_key_rejects_traversal_and_escape():
    for bad in [
        "",
        "/etc/passwd",
        "dossiers/../etc/passwd",
        "..\\windows\\secret.pdf",
        "file:///etc/passwd",
        "other/APP-25195/doc.pdf",
        "dossiers/APP-25195/nested/deep.pdf",
    ]:
        with pytest.raises(ValueError):
            validate_storage_key(bad)


def test_validate_storage_key_blocks_cross_application():
    with pytest.raises(ValueError, match="Cross-application"):
        validate_storage_key(VALID_KEY, application_id="APP-99999")


def test_sha_helpers_and_ttl_clamp():
    assert sha256_bytes(PAYLOAD) == PAYLOAD_SHA
    assert sha256_base64(PAYLOAD) == __import__("base64").b64encode(
        hashlib.sha256(PAYLOAD).digest()
    ).decode()
    assert is_valid_sha256_hex(PAYLOAD_SHA) is True
    assert is_valid_sha256_hex("xyz") is False
    assert clamp_presigned_ttl(30) == 300
    assert clamp_presigned_ttl(7200) == 3600
    assert clamp_presigned_ttl(900) == 900


# -- S3 presigned upload + verification (mocked client) ---------------------

def _s3():
    return S3Storage(bucket_name="finscan-dossiers", s3_client=MagicMock())


def test_s3_presign_binds_key_checksum_sse_and_size():
    mock = MagicMock()
    mock.generate_presigned_post.return_value = {"url": "https://s3.post", "fields": {}}
    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock)

    grant = storage.generate_upload_url(VALID_KEY, PAYLOAD_SHA, "application/pdf", 900)

    assert grant["storage_key"] == VALID_KEY
    assert grant["expires_in"] == 900
    _, kwargs = mock.generate_presigned_post.call_args
    assert kwargs["Bucket"] == "finscan-dossiers"
    assert kwargs["Key"] == VALID_KEY
    flat = str(kwargs["Conditions"])
    assert "AES256" in flat and "content-length-range" in flat and "x-amz-checksum-sha256" in flat


def test_s3_presign_rejects_bad_key_or_digest():
    storage = _s3()
    with pytest.raises(ValueError):
        storage.generate_upload_url("../evil.pdf", PAYLOAD_SHA)
    with pytest.raises(ValueError):
        storage.generate_upload_url(VALID_KEY, "not-a-digest")


def test_s3_verify_integrity_via_recorded_checksum():
    import base64

    mock = MagicMock()
    mock.head_object.return_value = {
        "ChecksumSHA256": base64.b64encode(bytes.fromhex(PAYLOAD_SHA)).decode(),
        "ContentLength": len(PAYLOAD),
    }
    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock)

    receipt = storage.verify_integrity(VALID_KEY, PAYLOAD_SHA)

    assert receipt["verified_via"] == "s3_checksum"
    assert receipt["sha256"] == PAYLOAD_SHA


def test_s3_verify_integrity_tamper_raises():
    import base64

    mock = MagicMock()
    mock.head_object.return_value = {
        "ChecksumSHA256": base64.b64encode(b"\x00" * 32).decode(),
        "ContentLength": len(PAYLOAD),
    }
    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock)

    with pytest.raises(StorageTamperError, match="tamper"):
        storage.verify_integrity(VALID_KEY, PAYLOAD_SHA)


def test_s3_verify_integrity_rehash_fallback():
    mock = MagicMock()
    mock.head_object.return_value = {"ContentLength": len(PAYLOAD)}
    body = MagicMock()
    body.read.return_value = PAYLOAD
    mock.get_object.return_value = {"Body": body}
    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock)

    receipt = storage.verify_integrity(VALID_KEY, PAYLOAD_SHA)
    assert receipt["verified_via"] == "rehash"

    body.read.return_value = b"tampered bytes"
    with pytest.raises(StorageTamperError, match="mismatch"):
        storage.verify_integrity(VALID_KEY, PAYLOAD_SHA)


def test_s3_download_url_fail_closed_and_clamped():
    mock = MagicMock()
    mock.generate_presigned_url.return_value = "https://signed/x"
    storage = S3Storage(bucket_name="finscan-dossiers", s3_client=mock)

    assert storage.get_signed_url(VALID_KEY, expires_in=99999) == "https://signed/x"
    _, kwargs = mock.generate_presigned_url.call_args
    assert kwargs["ExpiresIn"] == 3600

    mock.generate_presigned_url.side_effect = RuntimeError("sts down")
    with pytest.raises(RuntimeError):
        storage.get_signed_url(VALID_KEY)


# -- Local relay tickets + verification ------------------------------------

def test_local_ticket_roundtrip_single_use_and_expiry(tmp_path: Path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))

    grant = storage.generate_upload_url(VALID_KEY, PAYLOAD_SHA)
    assert grant["mode"] == "api_relay"
    assert storage.verify_upload_ticket(grant["ticket"], VALID_KEY, PAYLOAD_SHA) is True
    # Replay rejected
    assert storage.verify_upload_ticket(grant["ticket"], VALID_KEY, PAYLOAD_SHA) is False
    # Wrong digest rejected
    grant2 = storage.generate_upload_url(VALID_KEY, PAYLOAD_SHA)
    assert storage.verify_upload_ticket(grant2["ticket"], VALID_KEY, "0" * 64) is False


def test_local_verify_integrity(tmp_path: Path):
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))
    storage.put(VALID_KEY, PAYLOAD)

    receipt = storage.verify_integrity(VALID_KEY, PAYLOAD_SHA)
    assert receipt["sha256"] == PAYLOAD_SHA
    assert receipt["size_bytes"] == len(PAYLOAD)

    storage.put(VALID_KEY, b"tampered")
    with pytest.raises(StorageTamperError):
        storage.verify_integrity(VALID_KEY, PAYLOAD_SHA)
