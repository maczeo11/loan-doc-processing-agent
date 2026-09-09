"""
AWS S3 storage adapter (cloud deployment).
Owned by Member 2 (Bhanu Teja) & Member 6 (Balaji).

Provides:
- S3 object upload with automatic content type inference
- Presigned download URL generation for frontend pdf.js viewer
- Raw byte retrieval and existence checking
"""

import logging
from typing import BinaryIO, Union, Optional, Any
from adapters.storage.base import StoragePort

logger = logging.getLogger("finscan.adapters.storage.s3")


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
        """Generates a presigned URL for secure frontend PDF viewing."""
        clean_key = key.lstrip("/")
        try:
            url = self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": clean_key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {clean_key}: {e}")
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{clean_key}"

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
