"""
OCR Router: Decides page-by-page extraction path.
Order: PyMuPDF native text -> PaddleOCR CPU -> Optional managed Textract.
Owned by Member 3 (Jeevan).

Invariants & Guarantees from AGENTS.md:
- OCR routing occurs before document classification.
- Never train custom OCR models; use pre-trained engines only.
- AWS Textract fallback is hard-capped in code under 100 total pages and disabled by default.
- Every extracted fact/span receives a valid EvidenceRef.
"""

import logging
import os
from typing import List, Dict, Any, Union
from core.contracts.evidence import EvidenceRef
from core.extraction.native_parser import (
    extract_native_text_with_coordinates,
    extract_page_content,
)
from core.extraction.paddle_parser import extract_scanned_text_with_ocr

logger = logging.getLogger(__name__)

# Hard budget safety guards mandated by AGENTS.md
MAX_TEXTRACT_PAGES = 100
_TEXTRACT_PAGES_CONSUMED = 0
TEXTRACT_ENABLED = os.getenv("FINSCAN_ENABLE_TEXTRACT", "false").lower() in ("true", "1", "yes")


def get_textract_usage_count() -> int:
    """Returns the total number of AWS Textract pages processed across runtime."""
    return _TEXTRACT_PAGES_CONSUMED


def reset_textract_usage_count():
    """Resets the Textract counter (used primarily in test suites)."""
    global _TEXTRACT_PAGES_CONSUMED
    _TEXTRACT_PAGES_CONSUMED = 0


def inspect_page_route(
    pdf_input: Union[str, bytes],
    page_number: int,
    min_char_threshold: int = 50,
    min_word_threshold: int = 5,
) -> Dict[str, Any]:
    """
    Analyzes page properties to determine the optimal perception route.
    Returns metadata and selected route ('pymupdf_native' or 'paddleocr_cpu').
    """
    layout = extract_page_content(pdf_input, page_number)
    char_count = layout.get("char_count", 0)
    word_count = layout.get("word_count", 0)

    if char_count >= min_char_threshold and word_count >= min_word_threshold:
        return {
            "page_number": page_number,
            "route": "pymupdf_native",
            "reason": f"Native text layer present ({char_count} chars, {word_count} words)",
            "char_count": char_count,
            "word_count": word_count,
            "page_width": layout.get("page_width", 0.0),
            "page_height": layout.get("page_height", 0.0),
        }

    return {
        "page_number": page_number,
        "route": "paddleocr_cpu",
        "reason": f"Scanned or sparse text ({char_count} chars < {min_char_threshold} threshold)",
        "char_count": char_count,
        "word_count": word_count,
        "page_width": layout.get("page_width", 0.0),
        "page_height": layout.get("page_height", 0.0),
    }


def route_page_extraction(
    pdf_input: Union[str, bytes],
    page_number: int,
    document_id: str = "DOC-UNKNOWN",
    document_type: str = "unknown",
    min_char_threshold: int = 50,
    min_word_threshold: int = 5,
) -> List[EvidenceRef]:
    """
    Evaluates page properties and dynamically routes extraction:
    1. If usable native text layer present -> PyMuPDF with exact coordinates.
    2. If scanned / sparse text -> PaddleOCR on CPU.
    3. If CPU OCR produces nothing and Textract is enabled -> AWS Textract fallback (hard-capped < 100 pages).
    """
    decision = inspect_page_route(
        pdf_input=pdf_input,
        page_number=page_number,
        min_char_threshold=min_char_threshold,
        min_word_threshold=min_word_threshold,
    )

    route = decision["route"]
    logger.info(f"Routing document {document_id} page {page_number} via {route} ({decision['reason']})")

    # Route 1: PyMuPDF Native Text Layer
    if route == "pymupdf_native":
        evidence = extract_native_text_with_coordinates(
            pdf_input=pdf_input,
            page_number=page_number,
            document_id=document_id,
            document_type=document_type,
        )
        if evidence:
            return evidence

    # Route 2: Scanned Fallback via local PaddleOCR CPU
    logger.info(f"Executing CPU PaddleOCR fallback for {document_id} page {page_number}")
    ocr_evidence = extract_scanned_text_with_ocr(
        pdf_input=pdf_input,
        page_number=page_number,
        document_id=document_id,
        document_type=document_type,
    )
    if ocr_evidence:
        return ocr_evidence

    # Route 3: Managed Cloud OCR Fallback (Hard-Capped Under 100 Pages, Disabled by Default)
    if TEXTRACT_ENABLED:
        textract_evidence = call_textract_fallback_guarded(
            pdf_input=pdf_input,
            page_number=page_number,
            document_id=document_id,
            document_type=document_type,
        )
        if textract_evidence:
            return textract_evidence

    return []


def call_textract_fallback_guarded(
    pdf_input: Union[str, bytes],
    page_number: int,
    document_id: str,
    document_type: str,
) -> List[EvidenceRef]:
    """
    Selective managed OCR path.
    Enforces inviolable hard ceiling: under 100 pages total across runtime.
    """
    global _TEXTRACT_PAGES_CONSUMED

    if _TEXTRACT_PAGES_CONSUMED >= MAX_TEXTRACT_PAGES:
        logger.error(
            f"Textract spend guard triggered: Exceeded hard ceiling of {MAX_TEXTRACT_PAGES} pages. "
            f"Aborting Textract invocation for {document_id} page {page_number}."
        )
        return []

    _TEXTRACT_PAGES_CONSUMED += 1
    logger.warning(
        f"Invoked managed Textract for page {page_number} (Page {_TEXTRACT_PAGES_CONSUMED}/{MAX_TEXTRACT_PAGES})"
    )

    # In production, boto3 textract call would sit behind an adapter if enabled.
    return []
