"""
AWS S3 storage adapter (demo day cloud deployment).
"""

from typing import BinaryIO
from adapters.storage.base import StoragePort


class S3Storage(StoragePort):
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.region = region

    def put(self, key: str, data: BinaryIO) -> str:
        # TODO: Member 6 implement S3 put_object via boto3
        return f"s3://{self.bucket_name}/{key}"

    def get(self, key: str) -> bytes:
        # TODO: Member 6 implement S3 get_object via boto3
        return b""

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        # TODO: Member 6 implement generate_presigned_url
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
