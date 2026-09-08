"""
Native PDF parser using PyMuPDF (fitz) for text and exact word bounding boxes.
"""

from typing import List
from core.contracts.evidence import EvidenceRef


def extract_native_text_with_coordinates(pdf_path: str, page_number: int) -> List[EvidenceRef]:
    """
    Extracts text spans and bounding boxes via page.get_text('dict').
    """
    # TODO: Member 3 (Jeevan) implement PyMuPDF coordinate extraction
    return []
