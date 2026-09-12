"""
Native PDF parser using PyMuPDF (fitz) for text, word coordinates, and bounding boxes.
Owned by Member 3 (Jeevan).

Invariants & Guarantees:
- Every extracted fact/span retains bounding-box coordinates for audit provenance.
- Page coordinates are strictly validated and clamped against page bounds (0 <= x0 <= x1 <= width, 0 <= y0 <= y1 <= height).
- Supports both filesystem paths and raw PDF byte buffers.
"""

import logging
from typing import List, Dict, Any, Optional, Union
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
from core.contracts.evidence import EvidenceRef, BoundingBox

logger = logging.getLogger(__name__)


def validate_and_clamp_bbox(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    page_width: float,
    page_height: float,
) -> BoundingBox:
    """
    Validates and clamps bounding-box coordinates to page dimensions.
    Protects against negative values or corrupted coordinates exceeding page canvas.
    """
    safe_x0 = max(0.0, min(float(x0), float(page_width)))
    safe_y0 = max(0.0, min(float(y0), float(page_height)))
    safe_x1 = max(safe_x0, min(float(x1), float(page_width)))
    safe_y1 = max(safe_y0, min(float(y1), float(page_height)))

    return BoundingBox(
        x0=round(safe_x0, 2),
        y0=round(safe_y0, 2),
        x1=round(safe_x1, 2),
        y1=round(safe_y1, 2),
        page_width=round(float(page_width), 2),
        page_height=round(float(page_height), 2),
    )


def open_pdf_document(pdf_input: Union[str, bytes]) -> Any:
    """
    Opens a PDF document from a filesystem path or in-memory byte buffer.
    """
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) is not installed in the current environment.")
    if isinstance(pdf_input, bytes):
        return fitz.open(stream=pdf_input, filetype="pdf")
    if isinstance(pdf_input, str):
        return fitz.open(pdf_input)
    raise TypeError(f"Expected str path or bytes, got {type(pdf_input).__name__}")


def extract_native_text_with_coordinates(
    pdf_input: Union[str, bytes],
    page_number: int,
    document_id: str = "DOC-UNKNOWN",
    document_type: str = "unknown",
    doc: Any = None,
) -> List[EvidenceRef]:
    """
    Extracts text spans with exact bounding-box coordinates from a 1-indexed page.
    Returns a list of EvidenceRef items with 'pymupdf_native' extraction method.

    `doc`: an already-open fitz.Document, when the caller is probing/extracting
    several pages of the same PDF back-to-back (e.g. the OCR router) and wants to
    avoid reopening and reparsing the file for every call. Owned by the caller in
    that case - this function never closes a `doc` it did not open itself.
    """
    if page_number < 1:
        raise ValueError(f"Page numbers must be 1-indexed (got {page_number})")

    owns_doc = doc is None
    if owns_doc:
        doc = open_pdf_document(pdf_input)
    try:
        if page_number > len(doc):
            return []

        page = doc[page_number - 1]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        evidence_items: List[EvidenceRef] = []
        page_dict = page.get_text("dict")
        extraction_method = "pymupdf_native"

        # Pure native only: no hidden OCR side-effect here.
        # Scanned/image pages return [] so the router can escalate to
        # Tesseract CPU -> PaddleOCR -> Textract (DetectDocumentText, capped).
        has_native_spans = False
        for b in page_dict.get("blocks", []):
            for line in b.get("lines", []):
                for s in line.get("spans", []):
                    if s.get("text", "").strip():
                        has_native_spans = True
                        break
                if has_native_spans:
                    break
            if has_native_spans:
                break

        if not has_native_spans:
            return []

        for block in page_dict.get("blocks", []):
            if "lines" not in block:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_text = span.get("text", "").strip()
                    if not span_text:
                        continue

                    bbox_coords = span.get("bbox", (0.0, 0.0, 0.0, 0.0))
                    bbox = validate_and_clamp_bbox(
                        x0=bbox_coords[0],
                        y0=bbox_coords[1],
                        x1=bbox_coords[2],
                        y1=bbox_coords[3],
                        page_width=page_width,
                        page_height=page_height,
                    )

                    evidence_items.append(
                        EvidenceRef(
                            document_id=document_id,
                            document_type=document_type,
                            page_number=page_number,
                            quoted_span=span_text,
                            bounding_box=bbox,
                            extraction_method=extraction_method,
                            confidence=0.95 if extraction_method == "paddleocr_cpu" else 1.0,
                        )
                    )

        return evidence_items
    finally:
        if owns_doc:
            doc.close()


def extract_page_content(
    pdf_input: Union[str, bytes],
    page_number: int,
    doc: Any = None,
) -> Dict[str, Any]:
    """
    Extracts rich page layout details including raw text, word count, character count,
    and word-level bounding boxes. Used by OCR router and entity extractors.

    `doc`: an already-open fitz.Document to reuse instead of reopening `pdf_input`
    (see extract_native_text_with_coordinates). Caller-owned; never closed here.
    """
    if page_number < 1:
        raise ValueError(f"Page numbers must be 1-indexed (got {page_number})")

    owns_doc = doc is None
    if owns_doc:
        doc = open_pdf_document(pdf_input)
    try:
        if page_number > len(doc):
            return {
                "page_number": page_number,
                "page_width": 0.0,
                "page_height": 0.0,
                "text": "",
                "char_count": 0,
                "word_count": 0,
                "words": [],
            }

        page = doc[page_number - 1]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        raw_text = page.get_text("text") or ""
        words_raw = page.get_text("words") or []

        # Pure native probe: no OCR side-effect. Router decides escalation.
        # (Previously this did a hidden get_textpage_ocr when <20 chars,
        # which inflated char_count and forced every scan to "native".)

        words_formatted = []
        for w in words_raw:
            # fitz words tuple: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            w_text = w[4].strip()
            if not w_text:
                continue
            bbox = validate_and_clamp_bbox(
                x0=w[0],
                y0=w[1],
                x1=w[2],
                y1=w[3],
                page_width=page_width,
                page_height=page_height,
            )
            words_formatted.append({
                "word": w_text,
                "bbox": bbox,
                "block_no": w[5],
                "line_no": w[6],
                "word_no": w[7],
            })

        return {
            "page_number": page_number,
            "page_width": round(float(page_width), 2),
            "page_height": round(float(page_height), 2),
            "text": raw_text,
            "char_count": len(raw_text.strip()),
            "word_count": len(words_formatted),
            "words": words_formatted,
        }
    finally:
        if owns_doc:
            doc.close()


def find_phrase_evidence(
    pdf_input: Union[str, bytes],
    page_number: int,
    query: str,
    document_id: str = "DOC-UNKNOWN",
    document_type: str = "unknown",
    confidence: float = 1.0,
) -> Optional[EvidenceRef]:
    """
    Locates a target phrase or number on a specific page and builds a consolidated EvidenceRef.
    Merges matching rectangles if the phrase spans multiple boxes on the line.
    Falls back to OCR if phrase is not found in native layer.
    """
    if not query or not query.strip():
        return None
    if page_number < 1:
        raise ValueError(f"Page numbers must be 1-indexed (got {page_number})")

    doc = open_pdf_document(pdf_input)
    try:
        if page_number > len(doc):
            return None

        page = doc[page_number - 1]
        matches = page.search_for(query.strip())
        method = "pymupdf_native"

        if not matches:
            # Try searching with OCR textpage (Tesseract CPU via MuPDF)
            try:
                ocr_tp = page.get_textpage_ocr(dpi=200)
                ocr_matches = page.search_for(query.strip(), textpage=ocr_tp)
                if ocr_matches:
                    matches = ocr_matches
                    method = "tesseract_cpu"
            except Exception as e:
                logger.debug(f"OCR textpage search_for failed: {e}")

        if not matches:
            return None

        first_match = matches[0]
        # Union rect across all match segments if query wraps across tokens
        union_rect = fitz.Rect(first_match)
        for rect in matches[1:]:
            # If on the same horizontal line or contiguous block
            if abs(rect.y0 - first_match.y0) < 15.0:
                union_rect |= rect

        bbox = validate_and_clamp_bbox(
            x0=union_rect.x0,
            y0=union_rect.y0,
            x1=union_rect.x1,
            y1=union_rect.y1,
            page_width=page.rect.width,
            page_height=page.rect.height,
        )

        return EvidenceRef(
            document_id=document_id,
            document_type=document_type,
            page_number=page_number,
            quoted_span=query.strip(),
            bounding_box=bbox,
            extraction_method=method,
            confidence=0.85 if method == "tesseract_cpu" else confidence,
        )
    finally:
        doc.close()


def get_page_image_coverage(pdf_input: Union[str, bytes], page_number: int, doc: Any = None) -> float:
    """
    Fraction (0.0-1.0) of page area covered by raster images.
    Used by router to prefer OCR for image-heavy pages even when a small
    native layer exists (e.g. stamp + scan). Pure probe, no OCR.

    `doc`: an already-open fitz.Document to reuse (see extract_page_content).
    Caller-owned; never closed here.
    """
    if fitz is None:
        return 0.0
    owns_doc = doc is None
    if owns_doc:
        doc = open_pdf_document(pdf_input)
    try:
        if page_number > len(doc):
            return 0.0
        page = doc[page_number - 1]
        rect = page.rect
        page_area = float(rect.width * rect.height) or 1.0
        img_area = 0.0
        try:
            for img in page.get_images(full=True):
                try:
                    bbox = page.get_image_bbox(img)
                    img_area += float(bbox.width * bbox.height)
                except Exception:
                    continue
        except Exception:
            return 0.0
        return max(0.0, min(1.0, img_area / page_area))
    finally:
        if owns_doc:
            doc.close()


def extract_all_pages_content(pdf_input: Union[str, bytes]) -> List[Dict[str, Any]]:
    """
    Extracts structured page content and layout dictionaries for all pages in a document.
    Convenience method used by fact extractors and node pipelines.
    Pure native (no OCR side-effect); router escalates per page as needed.
    """
    doc = open_pdf_document(pdf_input)
    try:
        page_count = len(doc)
    finally:
        doc.close()

    return [extract_page_content(pdf_input, p) for p in range(1, page_count + 1)]

