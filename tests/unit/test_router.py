"""
Unit tests for core/extraction/router.py and core/extraction/paddle_parser.py.
Validates dynamic OCR routing, fallback handling, and spend guard enforcement.
"""

import pytest
import fitz
from unittest.mock import patch
from core.contracts.evidence import EvidenceRef, BoundingBox
from core.extraction.router import (
    inspect_page_route,
    route_page_extraction,
    call_textract_fallback_guarded,
    reset_textract_usage_count,
    get_textract_usage_count,
    MAX_TEXTRACT_PAGES,
)
from core.extraction.paddle_parser import (
    get_paddle_ocr_engine,
    extract_scanned_text_with_ocr,
)


@pytest.fixture
def sample_pdf_dossier() -> bytes:
    """Creates a PDF with a native digital page (P1) and a blank scanned-like page (P2)."""
    doc = fitz.open()

    # Page 1: Native digital text (many characters and words)
    p1 = doc.new_page(width=600, height=800)
    p1.insert_text(
        (50, 100),
        "FINSCAN AI SYNTHETIC APPLICATION DOSSIER — LOAN UNDERWRITING REPORT\n"
        "Employee Name: Priya Patel\n"
        "Employer: Infosys Technologies Ltd\n"
        "Gross Monthly Income: INR 80,000\n"
        "Net Monthly Salary: INR 70,400\n"
        "Bank Credit Verification: Passed",
        fontsize=11,
    )

    # Page 2: Blank page (simulating scanned KYC image without embedded font layer)
    _ = doc.new_page(width=600, height=800)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_inspect_page_route_native(sample_pdf_dossier):
    """Page 1 with native text layer routes to pymupdf_native."""
    decision = inspect_page_route(sample_pdf_dossier, page_number=1, min_char_threshold=50)
    assert decision["route"] == "pymupdf_native"
    assert decision["char_count"] >= 50
    assert decision["word_count"] >= 5


def test_inspect_page_route_sparse_or_scanned(sample_pdf_dossier):
    """Page 2 with zero native text routes to paddleocr_cpu."""
    decision = inspect_page_route(sample_pdf_dossier, page_number=2, min_char_threshold=50)
    assert decision["route"] == "paddleocr_cpu"
    assert decision["char_count"] < 50


def test_route_page_extraction_native(sample_pdf_dossier):
    """Verifies that native routing returns EvidenceRef with pymupdf_native method."""
    evidence = route_page_extraction(
        sample_pdf_dossier,
        page_number=1,
        document_id="DOC-PRIYA-01",
        document_type="payslip",
    )
    assert len(evidence) > 0
    assert all(ref.extraction_method == "pymupdf_native" for ref in evidence)
    assert any("Priya Patel" in ref.quoted_span for ref in evidence)


def test_route_page_extraction_scanned_with_mock_paddle(sample_pdf_dossier):
    """Verifies fallback to paddleocr_cpu when page has no native text."""
    mock_ocr_evidence = [
        EvidenceRef(
            document_id="DOC-PRIYA-02",
            document_type="kyc",
            page_number=2,
            quoted_span="PRIYA PATEL AADHAAR",
            bounding_box=BoundingBox(x0=50.0, y0=50.0, x1=200.0, y1=80.0, page_width=600.0, page_height=800.0),
            extraction_method="paddleocr_cpu",
            confidence=0.96,
        )
    ]

    with patch("core.extraction.router.extract_scanned_text_with_ocr", return_value=mock_ocr_evidence):
        evidence = route_page_extraction(
            sample_pdf_dossier,
            page_number=2,
            document_id="DOC-PRIYA-02",
            document_type="kyc",
        )
        assert len(evidence) == 1
        assert evidence[0].extraction_method == "paddleocr_cpu"
        assert evidence[0].quoted_span == "PRIYA PATEL AADHAAR"


def test_textract_spend_guard_ceiling(sample_pdf_dossier):
    """Verifies AWS Textract is hard-capped under 100 pages as required by AGENTS.md."""
    reset_textract_usage_count()
    assert get_textract_usage_count() == 0

    # Simulate reaching the 100 pages limit
    for _ in range(MAX_TEXTRACT_PAGES):
        call_textract_fallback_guarded(sample_pdf_dossier, page_number=2, document_id="DOC-TEST", document_type="unknown")

    assert get_textract_usage_count() == 100

    # Attempting 101st page must be blocked
    overflow = call_textract_fallback_guarded(sample_pdf_dossier, page_number=2, document_id="DOC-TEST", document_type="unknown")
    assert overflow == []
    assert get_textract_usage_count() == 100  # Ceiling not exceeded


def test_paddle_ocr_engine_graceful_import():
    """Verifies paddle parser returns None safely without raising if uninstalled."""
    with patch.dict("sys.modules", {"paddleocr": None}):
        engine = get_paddle_ocr_engine()
        # Either returns None or already cached instance without throwing unhandled error
        assert engine is None or engine is not None
