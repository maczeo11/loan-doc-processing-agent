"""
StoragePort: Storage abstraction protocol for local filesystem and AWS S3.

Security model (AGENTS.md 5.5):
- Every upload key MUST validate via validate_storage_key() before any presigned
  URL is minted or any completion is accepted (tenant isolation).
- Every completed upload MUST verify via verify helpers: client-declared SHA-256
  is recomputed server-side; mismatch raises StorageTamperError and the object
  must be treated as untrusted (caller deletes/quarantines it).
"""

import base64
import hashlib
import re
from typing import Any, BinaryIO, Dict, Protocol, Union

__all__ = [
    "StoragePort",
    "StorageTamperError",
    "sanitize_filename",
    "build_storage_key",
    "validate_storage_key",
    "sha256_bytes",
    "sha256_base64",
    "is_valid_sha256_hex",
    "clamp_presigned_ttl",
    "MIN_PRESIGNED_TTL_SECONDS",
    "MAX_PRESIGNED_TTL_SECONDS",
]

#: Short-lived URL bounds from AGENTS.md 5.5 (15-60 minutes).
MIN_PRESIGNED_TTL_SECONDS = 300
MAX_PRESIGNED_TTL_SECONDS = 3600

#: Canonical dossier key shape: dossiers/{application_id}/{document_id}_{file}
_STORAGE_KEY_RE = re.compile(r"^dossiers/[A-Za-z0-9][A-Za-z0-9\-_]*/[^/]+$")


class StorageTamperError(ValueError):
    """Raised when stored bytes do not match the declared SHA-256 digest."""


class StoragePort(Protocol):
    def put(self, key: str, data: Union[BinaryIO, bytes]) -> str:
        """Store an object and return its URI."""
        ...

    def get(self, key: str) -> bytes:
        """Retrieve raw bytes for an object key."""
        ...

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a short-lived download URL."""
        ...

    def generate_upload_url(
        self,
        key: str,
        content_sha256_hex: str,
        content_type: str = "application/pdf",
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """Mint a short-lived direct-upload grant bound to key + SHA-256."""
        ...

    def verify_integrity(self, key: str, expected_sha256_hex: str) -> Dict[str, Any]:
        """Recompute SHA-256 server-side; raise StorageTamperError on mismatch."""
        ...


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes filename: strips path traversals, replaces special chars with underscores,
    and preserves file extension for MIME resolution.
    """
    import os
    import re

    # Normalize backslashes to forward slashes for cross-platform OS compatibility
    normalized = filename.replace("\\", "/")
    base = os.path.basename(normalized).strip()
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    return safe or "document.pdf"


def build_storage_key(application_id: str, document_id: str, filename: str) -> str:
    """
    Authoritative FinScan AI storage key convention (Option B - Flattened Composite):
    dossiers/{application_id}/{document_id}_{sanitized_filename}

    Guarantees:
    - Scoped by application_id for hard tenant isolation and batch cleanup.
    - Disambiguated by document_id prefix to prevent filename collision.
    - Flattens all dossier documents into one directory level without nested single-file folders.
    """
    safe_name = sanitize_filename(filename)
    return f"dossiers/{application_id}/{document_id}_{safe_name}"


def validate_storage_key(key: str, application_id: str = "") -> str:
    """
    Enforces tenant isolation on a storage key. Returns the cleaned key.

    Rejects: empty keys, absolute paths, backslashes, '..' segments, keys
    outside dossiers/, nested subfolders, and (when application_id is given)
    keys scoped to a different application.
    """
    if not key or not key.strip():
        raise ValueError("Storage key cannot be empty")
    clean = key.strip().replace("\\", "/")
    if clean.startswith("/") or clean.startswith("file://") or ".." in clean.split("/"):
        raise ValueError(f"Directory traversal detected for storage key: {key}")
    if not _STORAGE_KEY_RE.match(clean):
        raise ValueError(
            f"Storage key must match dossiers/{{application_id}}/{{document_id}}_{{file}}: {key}"
        )
    if application_id:
        prefix = f"dossiers/{application_id}/"
        if not clean.startswith(prefix):
            raise ValueError(
                f"Cross-application key access blocked: key '{clean}' is outside '{prefix}'"
            )
    return clean


def sha256_bytes(data: bytes) -> str:
    """Hex SHA-256 digest of in-memory bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_base64(data: bytes) -> str:
    """Base64 SHA-256 digest (S3 x-amz-checksum-sha256 wire format)."""
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def is_valid_sha256_hex(value: object) -> bool:
    """True when value is a 64-char lowercase hex SHA-256 digest."""
    return isinstance(value, str) and _SHA256_HEX_RE.match(value) is not None


def re_fullmatch_sha256(value: object) -> bool:
    """Alias kept for adapter call sites validating declared digests."""
    return is_valid_sha256_hex(value)


def clamp_presigned_ttl(expires_in: int) -> int:
    """Clamps presigned URL TTL into the mandated 5-60 minute window."""
    try:
        ttl = int(expires_in)
    except (TypeError, ValueError):
        ttl = MAX_PRESIGNED_TTL_SECONDS
    return max(MIN_PRESIGNED_TTL_SECONDS, min(MAX_PRESIGNED_TTL_SECONDS, ttl))

