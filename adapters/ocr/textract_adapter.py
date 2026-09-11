"""
AWS Textract adapter (DetectDocumentText only — $0.0015/page).
Owned by Member 2 (cloud). core/ never imports boto3; router lazy-loads this.
"""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def detect_text_page(image_bytes: bytes) -> List[dict]:
    """
    Call Textract DetectDocumentText on a single page PNG.
    Returns [{text, confidence, bbox_norm:{Left,Top,Width,Height}}] for LINE blocks.
    Raises on missing creds/region so caller can fall back to UNKNOWN.
    """
    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise RuntimeError("boto3 not installed") from exc

    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-south-2"))
    client = boto3.client("textract", region_name=region)
    resp = client.detect_document_text(Document={"Bytes": image_bytes})
    out: List[dict] = []
    for block in resp.get("Blocks", []):
        if block.get("BlockType") != "LINE":
            continue
        text = (block.get("Text") or "").strip()
        if not text:
            continue
        geo = (block.get("Geometry") or {}).get("BoundingBox") or {}
        out.append(
            {
                "text": text,
                "confidence": float(block.get("Confidence", 99.0)) / 100.0,
                "bbox_norm": {
                    "Left": float(geo.get("Left", 0.0)),
                    "Top": float(geo.get("Top", 0.0)),
                    "Width": float(geo.get("Width", 1.0)),
                    "Height": float(geo.get("Height", 0.02)),
                },
            }
        )
    return out
