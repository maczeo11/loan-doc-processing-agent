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
