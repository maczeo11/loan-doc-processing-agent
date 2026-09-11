"""OCR ports: core/ must never import boto3 directly (AGENTS.md §3)."""

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class TextractPort(Protocol):
    def detect_text(self, image_bytes: bytes) -> List[dict]:
        """Return Textract LINE blocks: {text, confidence, bbox_norm}."""
        ...
