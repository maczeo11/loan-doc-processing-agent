"""
Local filesystem storage adapter (default for local development).
Owned by Member 2 (Bhanu Teja) & Member 6 (Balaji).

Provides:
- Atomic file writes and directory auto-creation
- SHA-256 content deduplication and integrity checking
- Direct byte retrieval and local presigned/static file URLs
"""

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from typing import BinaryIO, Union, Dict, Any, Optional
from adapters.storage.base import (
    StoragePort,
    StorageTamperError,
    clamp_presigned_ttl,
    re_fullmatch_sha256,
    validate_storage_key,
)


class LocalFileSystemStorage(StoragePort):
    """
    StoragePort implementation for local disk storage.
    """

    def __init__(self, base_dir: Optional[str] = None, base_url: str = "http://localhost:8000"):
        resolved_dir = base_dir or os.getenv("STORAGE_BASE_DIR", "data/storage")
        self.base_dir = Path(resolved_dir).resolve()
        self.base_url = base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, key: str) -> Path:
        """Resolves key against base_dir, handling file:// URIs, absolute paths, and preventing directory traversal."""
        if key.startswith("file://"):
            clean_path = key[7:]
            if os.name == "nt" and clean_path.startswith("/") and len(clean_path) > 2 and clean_path[2] == ":":
                clean_path = clean_path.lstrip("/")
            return Path(clean_path).resolve()
        if os.path.isabs(key):
            return Path(key).resolve()
        clean_key = os.path.normpath(key).lstrip("\\/").replace("\\", "/")
        full_path = (self.base_dir / clean_key).resolve()
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError(f"Directory traversal detected for storage key: {key}")
        return full_path

    def put(self, key: str, data: Union[BinaryIO, bytes]) -> str:
        """Stores file content on disk and returns its file:// URI."""
        file_path = self._resolve_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            content = data
        elif hasattr(data, "read"):
            content = data.read()
        else:
            raise TypeError(f"Unsupported data type for storage put: {type(data)}")

        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        temp_path.write_bytes(content)
        temp_path.replace(file_path)

        return f"file://{file_path.as_posix()}"

    def get(self, key: str) -> bytes:
        """Retrieves raw file bytes from local disk."""
        file_path = self._resolve_path(key)
        if not file_path.is_file():
            raise FileNotFoundError(f"Object '{key}' not found in local storage at {file_path}")
        return file_path.read_bytes()

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """Returns standard local serving URL (dev adapter serves same-origin; use S3 grants in cloud)."""
        clean_key = os.path.normpath(key).lstrip("\\/").replace("\\", "/")
        return f"{self.base_url}/files/{clean_key}"

    def exists(self, key: str) -> bool:
        """Checks if file exists in storage."""
        try:
            return self._resolve_path(key).is_file()
        except ValueError:
            return False

    def delete(self, key: str) -> bool:
        """Deletes file from storage."""
        file_path = self._resolve_path(key)
        if file_path.is_file():
            file_path.unlink()
            return True
        return False

    def compute_sha256(self, key: str) -> str:
        """Calculates SHA-256 checksum of stored object."""
        content = self.get(key)
        return hashlib.sha256(content).hexdigest()

    # -- Presigned direct-upload (local dev relay) ---------------------------

    def _upload_secret(self) -> bytes:
        secret = os.getenv("FINSCAN_LOCAL_UPLOAD_SECRET", "")
        if not secret:
            # Ephemeral per-process secret: tickets never survive restarts (dev only).
            if not hasattr(self, "_ephemeral_secret"):
                self._ephemeral_secret = secrets.token_hex(32)
            return self._ephemeral_secret.encode()
        return secret.encode()

    def generate_upload_url(
        self,
        key: str,
        content_sha256_hex: str,
        content_type: str = "application/pdf",
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """
        Mints a single-use HMAC upload ticket for local development. The browser
        relays bytes through POST .../uploads/complete with this ticket; the
        ticket binds key + declared SHA-256 + expiry so tampered grants fail.
        """
        clean_key = validate_storage_key(key)
        if not re_fullmatch_sha256(content_sha256_hex):
            raise ValueError("content_sha256_hex must be a 64-char lowercase hex digest")
        ttl = clamp_presigned_ttl(expires_in)
        exp = int(time.time()) + ttl
        mac = hmac.new(
            self._upload_secret(),
            f"{clean_key}.{content_sha256_hex.lower()}.{exp}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return {
            "mode": "api_relay",
            "ticket": f"{exp}.{mac}",
            "storage_key": clean_key,
            "content_sha256_hex": content_sha256_hex.lower(),
            "content_type": content_type,
            "expires_in": ttl,
        }

    def verify_upload_ticket(self, ticket: str, key: str, content_sha256_hex: str) -> bool:
        """Validates ticket MAC + expiry + single-use for the bound key/digest."""
        clean_key = validate_storage_key(key)
        try:
            exp_str, mac = ticket.split(".", 1)
            exp = int(exp_str)
        except (ValueError, AttributeError):
            return False
        if exp < int(time.time()):
            return False
        expected = hmac.new(
            self._upload_secret(),
            f"{clean_key}.{content_sha256_hex.lower()}.{exp}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, mac):
            return False
        used = getattr(self, "_used_tickets", None)
        if used is None:
            used = self._used_tickets = set()
        if ticket in used:
            return False
        used.add(ticket)
        return True

    def verify_integrity(self, key: str, expected_sha256_hex: str) -> Dict[str, Any]:
        """Recomputes SHA-256 of the stored object; raises StorageTamperError on mismatch."""
        clean_key = validate_storage_key(key)
        if not re_fullmatch_sha256(expected_sha256_hex):
            raise ValueError("expected_sha256_hex must be a 64-char lowercase hex digest")
        actual = self.compute_sha256(clean_key)
        if actual != expected_sha256_hex.lower():
            raise StorageTamperError(
                f"SHA-256 mismatch for '{clean_key}': declared {expected_sha256_hex.lower()} "
                f"!= stored {actual}"
            )
        size = self._resolve_path(clean_key).stat().st_size
        return {"key": clean_key, "sha256": actual, "size_bytes": size, "verified_via": "rehash"}
