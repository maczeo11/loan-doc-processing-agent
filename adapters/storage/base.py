"""
StoragePort: Storage abstraction protocol for local filesystem and AWS S3.
"""

from typing import Protocol, BinaryIO


class StoragePort(Protocol):
    def put(self, key: str, data: BinaryIO) -> str:
        """Store an object and return its URI."""
        ...

    def get(self, key: str) -> bytes:
        """Retrieve raw bytes for an object key."""
        ...

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a short-lived download URL."""
        ...


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes filename: strips path traversals, replaces special chars with underscores,
    and preserves file extension for MIME resolution.
    """
    import os
    import re

    base = os.path.basename(filename).strip()
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

