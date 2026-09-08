"""
Local filesystem storage adapter (default for local development).
Owned by Member 2 (Bhanu Teja) & Member 6 (Balaji).

Provides:
- Atomic file writes and directory auto-creation
- SHA-256 content deduplication and integrity checking
- Direct byte retrieval and local presigned/static file URLs
"""

import os
import hashlib
from pathlib import Path
from typing import BinaryIO, Union
from adapters.storage.base import StoragePort


class LocalFileSystemStorage(StoragePort):
    """
    StoragePort implementation for local disk storage.
    """

    def __init__(self, base_dir: str = "data/storage", base_url: str = "http://localhost:8000"):
        self.base_dir = Path(base_dir).resolve()
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
        """Returns standard local serving URL for the file."""
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
