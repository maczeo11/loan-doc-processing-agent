"""
Unit tests for core/extraction/native_parser.py.
Validates PyMuPDF coordinate extraction, bounding box clamping, and EvidenceRef creation.
"""

import pytest
import fitz
from core.extraction.native_parser import (
    validate_and_clamp_bbox,
    extract_native_text_with_coordinates,
    extract_page_content,
    find_phrase_evidence,
)


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generates an in-memory PDF with known text and coordinates."""
    doc = fitz.open()

    # Page 1: Standard financial document layout
    page1 = doc.new_page(width=600, height=800)
    page1.insert_text((50, 100), "Employer: TechCorp Solutions Pvt Ltd", fontsize=12)
    page1.insert_text((50, 150), "Employee Name: Rajesh Sharma", fontsize=12)
    page1.insert_text((50, 200), "PAN: ABCDE1234F", fontsize=12)
    page1.insert_text((50, 250), "Gross Salary: INR 95,000", fontsize=12)
    page1.insert_text((50, 300), "Net Salary: INR 85,000", fontsize=12)

    # Page 2: Blank page (e.g. scanned image simulation)
    _ = doc.new_page(width=600, height=800)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_validate_and_clamp_bbox_bounds():
    """Verifies bounding-box clamping prevents coordinate exploits beyond canvas."""
    # Negative values clamped to 0
    bbox = validate_and_clamp_bbox(
        x0=-15.0,
        y0=-10.0,
        x1=100.0,
        y1=150.0,
        page_width=600.0,
        page_height=800.0,
    )
    assert bbox.x0 == 0.0
    assert bbox.y0 == 0.0
    assert bbox.x1 == 100.0
    assert bbox.y1 == 150.0

    # Values exceeding dimensions clamped to page width/height
    bbox2 = validate_and_clamp_bbox(
        x0=500.0,
        y0=750.0,
        x1=700.0,
        y1=900.0,
        page_width=600.0,
        page_height=800.0,
    )
    assert bbox2.x1 == 600.0
    assert bbox2.y1 == 800.0
    assert bbox2.x0 <= bbox2.x1
    assert bbox2.y0 <= bbox2.y1


def test_extract_native_text_with_coordinates(sample_pdf_bytes):
    """Verifies extraction of text spans and EvidenceRef generation."""
    evidence_list = extract_native_text_with_coordinates(
        sample_pdf_bytes,
        page_number=1,
        document_id="DOC-PAYSLIP-01",
        document_type="payslip",
    )

    assert len(evidence_list) > 0

    # Check evidence structure and invariants
    for ref in evidence_list:
        assert ref.document_id == "DOC-PAYSLIP-01"
        assert ref.document_type == "payslip"
        assert ref.page_number == 1
        assert ref.extraction_method == "pymupdf_native"
        assert ref.confidence == 1.0
        assert ref.bounding_box is not None
        assert 0.0 <= ref.bounding_box.x0 <= ref.bounding_box.x1 <= 600.0
        assert 0.0 <= ref.bounding_box.y0 <= ref.bounding_box.y1 <= 800.0

    # Verify specific text span exists
    spans = [ref.quoted_span for ref in evidence_list]
    assert any("TechCorp Solutions" in s for s in spans)
    assert any("Rajesh Sharma" in s for s in spans)


def test_extract_page_content(sample_pdf_bytes):
    """Verifies rich layout and word-level extraction."""
    content = extract_page_content(sample_pdf_bytes, page_number=1)

    assert content["page_number"] == 1
    assert content["page_width"] == 600.0
    assert content["page_height"] == 800.0
    assert content["char_count"] > 50
    assert content["word_count"] > 10
    assert "Rajesh Sharma" in content["text"]
    assert "Net Salary: INR 85,000" in content["text"]

    # Verify word bounding boxes
    words = content["words"]
    first_word = words[0]
    assert "word" in first_word
    assert first_word["bbox"].page_width == 600.0


def test_find_phrase_evidence(sample_pdf_bytes):
    """Verifies targeted phrase bounding box search."""
    evidence = find_phrase_evidence(
        sample_pdf_bytes,
        page_number=1,
        query="INR 85,000",
        document_id="DOC-PAYSLIP-01",
        document_type="payslip",
    )

    assert evidence is not None
    assert evidence.quoted_span == "INR 85,000"
    assert evidence.document_id == "DOC-PAYSLIP-01"
    assert evidence.page_number == 1
    assert evidence.bounding_box is not None
    assert evidence.bounding_box.y0 > 250.0  # Inserted around y=300


def test_find_phrase_evidence_not_found(sample_pdf_bytes):
    """Verifies None returned when target phrase is absent."""
    evidence = find_phrase_evidence(
        sample_pdf_bytes,
        page_number=1,
        query="Non-existent phrase 99999",
        document_id="DOC-PAYSLIP-01",
        document_type="payslip",
    )
    assert evidence is None


def test_empty_page_and_invalid_indices(sample_pdf_bytes):
    """Verifies graceful handling of empty pages and index boundary checks."""
    # Page 2 has no text
    p2_evidence = extract_native_text_with_coordinates(
        sample_pdf_bytes,
        page_number=2,
    )
    assert p2_evidence == []

    # Page 0 should raise ValueError (1-indexed invariant)
    with pytest.raises(ValueError):
        extract_native_text_with_coordinates(sample_pdf_bytes, page_number=0)

    with pytest.raises(ValueError):
        extract_page_content(sample_pdf_bytes, page_number=0)

    # Page beyond document length returns empty
    out_of_bounds = extract_native_text_with_coordinates(
        sample_pdf_bytes,
        page_number=99,
    )
    assert out_of_bounds == []
