"""
CPU-based PaddleOCR parser for scanned pages with no native text layer.
"""

from typing import List
from core.contracts.evidence import EvidenceRef


def extract_scanned_text_with_ocr(pdf_path: str, page_number: int) -> List[EvidenceRef]:
    """
    Renders page to image and runs PaddleOCR on CPU.
    """
    # TODO: Member 3 (Jeevan) implement PaddleOCR execution & coordinate extraction
    return []
