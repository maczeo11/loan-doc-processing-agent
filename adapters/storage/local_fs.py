import os
from typing import BinaryIO
from adapters.storage.base import StoragePort


class LocalFileSystemStorage(StoragePort):
    def __init__(self, base_dir: str = "data/storage"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def put(self, key: str, data: BinaryIO) -> str:
        clean_key = key.lstrip("/\\")
        full_path = os.path.join(self.base_dir, clean_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data.read())
        return f"file://{full_path}"

    def get(self, key: str) -> bytes:
        if key.startswith("file://"):
            clean_path = key[7:]
            if os.name == "nt" and clean_path.startswith("/") and len(clean_path) > 2 and clean_path[2] == ":":
                clean_path = clean_path.lstrip("/")
            full_path = clean_path
        elif os.path.isabs(key):
            full_path = key
        else:
            clean_key = key.lstrip("/\\")
            full_path = os.path.join(self.base_dir, clean_key)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Storage key '{key}' not found at '{full_path}'")
        with open(full_path, "rb") as f:
            return f.read()

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        return f"http://localhost:8000/files/{key}"
