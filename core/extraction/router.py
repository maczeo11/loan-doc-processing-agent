"""
OCR Router: Decides page-by-page extraction path.
Order: PyMuPDF native text -> PaddleOCR CPU -> Optional managed Textract.
"""

from typing import List, Dict, Any
from core.contracts.evidence import EvidenceRef


def route_page_extraction(pdf_path: str, page_number: int) -> List[EvidenceRef]:
    """
    Evaluates page properties and routes:
    1. If usable native text layer present -> PyMuPDF with exact coordinates.
    2. If scanned / unreadable -> PaddleOCR on CPU.
    3. AWS Textract fallback (hard-capped under 100 pages, off by default).
    """
    # TODO: Member 3 (Jeevan) implement routing logic
    return []


def _call_textract_fallback(image_bytes: bytes) -> List[Dict[str, Any]]:
    """Selective managed OCR path. Hard-capped under 100 pages in code."""
    # TODO: Member 3 implement if managed cloud OCR is required
    return []
