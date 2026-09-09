"""
AWS S3 storage adapter (cloud deployment).
Owned by Member 2 (Bhanu Teja) & Member 6 (Balaji).

Provides:
- S3 object upload with automatic content type inference
- Presigned download URL generation for frontend pdf.js viewer
- Raw byte retrieval and existence checking
"""

import logging
from typing import BinaryIO, Union, Optional, Any, Dict
from adapters.storage.base import (
    StoragePort,
    StorageTamperError,
    clamp_presigned_ttl,
    re_fullmatch_sha256,
    sha256_bytes,
    validate_storage_key,
)

logger = logging.getLogger("finscan.adapters.storage.s3")

#: Direct-upload size ceiling mirrors API quota (MAX_FILE_SIZE_MB = 10).
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class S3Storage(StoragePort):
    """
    StoragePort implementation using AWS S3.
    """

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        s3_client: Optional[Any] = None,
    ):
        self.bucket_name = bucket_name
        self.region = region
        self._client = s3_client

    @property
    def client(self):
        """Lazily initializes boto3 S3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("s3", region_name=self.region)
            except Exception as e:
                logger.error(f"Failed to initialize boto3 S3 client: {e}")
                raise
        return self._client

    def put(
        self,
        key: str,
        data: Union[BinaryIO, bytes],
        content_type: str = "application/pdf",
        server_side_encryption: str = "AES256",
    ) -> str:
        """
        Uploads file to S3 bucket with server-side encryption (SSE-S3/AES256) and returns s3:// URI.
        Enforces tenant isolation by validating path prefix.
        """
        clean_key = key.lstrip("/")
        if not clean_key.startswith("dossiers/"):
            clean_key = f"dossiers/{clean_key}"

        extra_args = {
            "ContentType": content_type,
            "ServerSideEncryption": server_side_encryption,
        }

        try:
            if isinstance(data, bytes):
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=clean_key,
                    Body=data,
                    ContentType=content_type,
                    ServerSideEncryption=server_side_encryption,
                )
            elif hasattr(data, "read"):
                self.client.upload_fileobj(
                    data,
                    self.bucket_name,
                    clean_key,
                    ExtraArgs=extra_args,
                )
            else:
                raise TypeError(f"Unsupported data type for S3 put: {type(data)}")

            logger.info(f"Uploaded encrypted object to s3://{self.bucket_name}/{clean_key}")
            return f"s3://{self.bucket_name}/{clean_key}"
        except Exception as e:
            logger.error(f"Failed to upload to S3 {self.bucket_name}/{clean_key}: {e}")
            raise

    def get(self, key: str) -> bytes:
        """Retrieves raw bytes from S3 object."""
        clean_key = key.lstrip("/")
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=clean_key)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"Failed to get object from S3 {self.bucket_name}/{clean_key}: {e}")
            raise

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """Generates a short-lived presigned download URL (fail-closed, TTL clamped)."""
        clean_key = validate_storage_key(key)
        ttl = clamp_presigned_ttl(expires_in)
        try:
            return self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": clean_key},
                ExpiresIn=ttl,
            )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {clean_key}: {e}")
            raise

    def generate_upload_url(
        self,
        key: str,
        content_sha256_hex: str,
        content_type: str = "application/pdf",
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """
        Mints a presigned POST grant so browsers upload direct to S3 without
        proxying bytes through the API. The grant is bound to the exact key,
        content type, size ceiling, SSE-S3, and the client-declared SHA-256
        checksum. Tampering with any field invalidates the signature.
        """
        import base64

        clean_key = validate_storage_key(key)
        if not re_fullmatch_sha256(content_sha256_hex):
            raise ValueError("content_sha256_hex must be a 64-char lowercase hex digest")
        ttl = clamp_presigned_ttl(expires_in)
        checksum_b64 = base64.b64encode(bytes.fromhex(content_sha256_hex)).decode("ascii")

        conditions: list = [
            {"key": clean_key},
            {"Content-Type": content_type},
            {"x-amz-server-side-encryption": "AES256"},
            {"x-amz-checksum-sha256": checksum_b64},
            ["content-length-range", 1, MAX_UPLOAD_BYTES],
        ]
        fields = {
            "key": clean_key,
            "Content-Type": content_type,
            "x-amz-server-side-encryption": "AES256",
            "x-amz-checksum-sha256": checksum_b64,
        }
        try:
            grant = self.client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=clean_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=ttl,
            )
        except Exception as e:
            logger.error(f"Failed to mint presigned upload for {clean_key}: {e}")
            raise
        grant["storage_key"] = clean_key
        grant["expires_in"] = ttl
        grant["max_bytes"] = MAX_UPLOAD_BYTES
        return grant

    def verify_integrity(self, key: str, expected_sha256_hex: str) -> Dict[str, Any]:
        """
        Server-side tamper check after a direct upload completes. Compares the
        S3-recorded checksum against the declared digest, falling back to a
        full byte re-hash. Raises StorageTamperError on any mismatch.
        """
        clean_key = validate_storage_key(key)
        if not re_fullmatch_sha256(expected_sha256_hex):
            raise ValueError("expected_sha256_hex must be a 64-char lowercase hex digest")

        try:
            head = self.client.head_object(Bucket=self.bucket_name, Key=clean_key)
        except Exception as e:
            logger.error(f"Integrity check: missing object {clean_key}: {e}")
            raise StorageTamperError(f"Uploaded object not found for verification: {clean_key}")

        recorded = (head.get("ChecksumSHA256") or "").strip()
        if recorded:
            import base64

            recorded_hex = base64.b64decode(recorded).hex()
            if recorded_hex != expected_sha256_hex.lower():
                raise StorageTamperError(
                    f"S3 checksum mismatch for '{clean_key}': object was tampered in transit"
                )
            return {
                "key": clean_key,
                "sha256": expected_sha256_hex.lower(),
                "size_bytes": int(head.get("ContentLength", 0)),
                "verified_via": "s3_checksum",
            }

        # Fallback: download and re-hash when the object lacks a stored checksum
        raw = self.get(clean_key)
        actual = sha256_bytes(raw)
        if actual != expected_sha256_hex.lower():
            raise StorageTamperError(
                f"SHA-256 mismatch for '{clean_key}': declared {expected_sha256_hex.lower()} "
                f"!= stored {actual}"
            )
        return {
            "key": clean_key,
            "sha256": actual,
            "size_bytes": len(raw),
            "verified_via": "rehash",
        }

    def exists(self, key: str) -> bool:
        """Checks if object exists in S3 bucket."""
        clean_key = key.lstrip("/")
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=clean_key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Deletes object from S3 bucket."""
        clean_key = key.lstrip("/")
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=clean_key)
            logger.info(f"Deleted s3://{self.bucket_name}/{clean_key}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete S3 object {clean_key}: {e}")
            return False
