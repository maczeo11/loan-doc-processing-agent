"""
Local filesystem storage adapter (default for local development).
"""

from typing import BinaryIO
from adapters.storage.base import StoragePort


class LocalFileSystemStorage(StoragePort):
    def __init__(self, base_dir: str = "data/storage"):
        self.base_dir = base_dir

    def put(self, key: str, data: BinaryIO) -> str:
        # TODO: Member 6 implement local file write
        return f"file://{self.base_dir}/{key}"

    def get(self, key: str) -> bytes:
        # TODO: Member 6 implement local file read
        return b""

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        return f"http://localhost:8000/files/{key}"
