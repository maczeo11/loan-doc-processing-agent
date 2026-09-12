"""
OCR Router: Decides page-by-page extraction path.
Order: PyMuPDF native text -> Tesseract CPU -> PaddleOCR CPU -> Managed Textract (Detect only).
Owned by Member 3 (Jeevan).

Invariants & Guarantees from AGENTS.md:
- OCR routing occurs before document classification.
- Never train custom OCR models; use pre-trained engines only.
- AWS Textract fallback is hard-capped in code under 100 total pages and disabled by default.
- Every extracted fact/span receives a valid EvidenceRef.
- core/ never imports boto3 (Textract lives in adapters/ocr/).
"""

import logging
import os
import time
from typing import List, Dict, Any, Optional, Union
from core.contracts.evidence import EvidenceRef
from core.extraction.native_parser import (
    extract_native_text_with_coordinates,
    extract_page_content,
    get_page_image_coverage,
)
from core.extraction.paddle_parser import extract_scanned_text_with_ocr

logger = logging.getLogger(__name__)

# Hard budget safety guards mandated by AGENTS.md
# DetectDocumentText only ($0.0015/page). NEVER AnalyzeDocument/Forms/Tables here.
MAX_TEXTRACT_PAGES = 100
_TEXTRACT_PAGES_CONSUMED = 0

# Escalation thresholds: a page stays on the native fast-path only when its
# text layer clears BOTH minimums and the page is not image-heavy. Raise the
# minimums to escalate MORE pages to OCR (easier escalation); lower them to
# keep more pages native (faster, cheaper). Resolved from env at call time so
# deployments can tune without code changes:
#   FINSCAN_OCR_MIN_CHARS (default 100), FINSCAN_OCR_MIN_WORDS (default 10),
#   FINSCAN_OCR_MAX_IMAGE_COVERAGE (default 0.5).
DEFAULT_MIN_CHAR_THRESHOLD = 100
DEFAULT_MIN_WORD_THRESHOLD = 10
DEFAULT_MAX_IMAGE_COVERAGE = 0.5


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except (ValueError, AttributeError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip())
    except (ValueError, AttributeError):
        return default


def _default_min_chars() -> int:
    return _env_int("FINSCAN_OCR_MIN_CHARS", DEFAULT_MIN_CHAR_THRESHOLD)


def _default_min_words() -> int:
    return _env_int("FINSCAN_OCR_MIN_WORDS", DEFAULT_MIN_WORD_THRESHOLD)


def _default_max_image_coverage() -> float:
    return _env_float("FINSCAN_OCR_MAX_IMAGE_COVERAGE", DEFAULT_MAX_IMAGE_COVERAGE)


def _textract_enabled() -> bool:
    return os.getenv("FINSCAN_ENABLE_TEXTRACT", "false").lower() in ("true", "1", "yes")


# Back-compat for tests that patch router.TEXTRACT_ENABLED directly.
TEXTRACT_ENABLED = _textract_enabled()


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
    min_char_threshold: Optional[int] = None,
    min_word_threshold: Optional[int] = None,
    max_image_coverage: Optional[float] = None,
    doc: Any = None,
) -> Dict[str, Any]:
    """
    Analyzes NATIVE-ONLY page properties to determine the optimal perception route.
    Pure probe: never runs OCR as a side-effect (that inflated char_count before).
    Returns metadata and selected route ('pymupdf_native' or 'tesseract_cpu').
    Unset thresholds resolve from FINSCAN_OCR_MIN_CHARS / FINSCAN_OCR_MIN_WORDS /
    FINSCAN_OCR_MAX_IMAGE_COVERAGE at call time.

    `doc`: an already-open fitz.Document, so probing many pages of one PDF (the
    common case - a caller walking every page of a document) opens/parses the file
    once instead of once per probe call. Caller-owned; never closed here.
    """
    min_chars = _default_min_chars() if min_char_threshold is None else min_char_threshold
    min_words = _default_min_words() if min_word_threshold is None else min_word_threshold
    max_img = _default_max_image_coverage() if max_image_coverage is None else max_image_coverage
    layout = extract_page_content(pdf_input, page_number, doc=doc)
    char_count = layout.get("char_count", 0)
    word_count = layout.get("word_count", 0)
    try:
        image_coverage = get_page_image_coverage(pdf_input, page_number, doc=doc)
    except Exception:
        image_coverage = 0.0

    # Image-heavy pages go to OCR even if a small native layer (stamp/header) exists.
    if char_count >= min_chars and word_count >= min_words and image_coverage < max_img:
        return {
            "page_number": page_number,
            "route": "pymupdf_native",
            "reason": f"Native text layer present ({char_count} chars, {word_count} words, img {image_coverage:.0%})",
            "char_count": char_count,
            "word_count": word_count,
            "image_coverage": round(image_coverage, 3),
            "page_width": layout.get("page_width", 0.0),
            "page_height": layout.get("page_height", 0.0),
        }

    return {
        "page_number": page_number,
        "route": "tesseract_cpu",
        "reason": f"Scanned or sparse text ({char_count} chars < {min_chars} threshold, img {image_coverage:.0%})",
        "char_count": char_count,
        "word_count": word_count,
        "image_coverage": round(image_coverage, 3),
        "page_width": layout.get("page_width", 0.0),
        "page_height": layout.get("page_height", 0.0),
    }


def route_page_extraction(
    pdf_input: Union[str, bytes],
    page_number: int,
    document_id: str = "DOC-UNKNOWN",
    document_type: str = "unknown",
    min_char_threshold: Optional[int] = None,
    min_word_threshold: Optional[int] = None,
    ocr_timeout_s: int = 60,
    doc: Any = None,
) -> List[EvidenceRef]:
    """
    Evaluates page properties and dynamically routes extraction:
    1. Usable native text layer -> PyMuPDF with exact coordinates.
    2. Scanned / sparse / image-heavy -> Tesseract CPU (dpi 200, retry 300) -> PaddleOCR where available.
    3. If CPU OCR empty and Textract enabled -> AWS Textract DetectDocumentText (hard-capped < 100 pages).
    Emits per-page route/reason/char_count/dpi/latency_ms logs for audit.

    `doc`: an already-open fitz.Document to reuse across the probe and the native
    extraction call below (see inspect_page_route) - avoids reopening/reparsing the
    same PDF up to 3x per page when a caller walks every page of one document.
    Caller-owned; never closed here.
    """
    t0 = time.monotonic()
    decision = inspect_page_route(
        pdf_input=pdf_input,
        page_number=page_number,
        min_char_threshold=min_char_threshold,
        min_word_threshold=min_word_threshold,
        doc=doc,
    )

    route = decision["route"]
    logger.info(f"Routing document {document_id} page {page_number} via {route} ({decision['reason']})")

    # Route 1: PyMuPDF Native Text Layer (pure native, no hidden OCR)
    if route == "pymupdf_native":
        evidence = extract_native_text_with_coordinates(
            pdf_input=pdf_input,
            page_number=page_number,
            document_id=document_id,
            document_type=document_type,
            doc=doc,
        )
        if evidence:
            logger.info(
                f"OCR route done doc={document_id} pg={page_number} route=pymupdf_native "
                f"chars={decision['char_count']} latency_ms={int((time.monotonic() - t0) * 1000)}"
            )
            return evidence
        logger.info(f"Native layer empty on retry for {document_id} p{page_number}; escalating to CPU OCR")

    # Route 2: CPU OCR with dpi ladder (200 fast, 300 accurate). extract_scanned_text_with_ocr
    # tries PaddleOCR where installed, else Tesseract via MuPDF, and labels honestly.
    for dpi in (200, 300):
        try:
            ocr_evidence = extract_scanned_text_with_ocr(
                pdf_input=pdf_input,
                page_number=page_number,
                document_id=document_id,
                document_type=document_type,
                dpi=dpi,
            )
        except Exception as exc:
            logger.warning(f"CPU OCR dpi={dpi} failed for {document_id} p{page_number}: {exc}")
            ocr_evidence = []
        if ocr_evidence:
            logger.info(
                f"OCR route done doc={document_id} pg={page_number} "
                f"route={ocr_evidence[0].extraction_method} dpi={dpi} "
                f"spans={len(ocr_evidence)} latency_ms={int((time.monotonic() - t0) * 1000)}"
            )
            return ocr_evidence

    # Route 3: Managed Cloud OCR Fallback (DetectDocumentText only, hard-capped, off by default)
    if _textract_enabled():
        textract_evidence = call_textract_fallback_guarded(
            pdf_input=pdf_input,
            page_number=page_number,
            document_id=document_id,
            document_type=document_type,
        )
        if textract_evidence:
            return textract_evidence

    logger.info(
        f"OCR route done doc={document_id} pg={page_number} route=UNKNOWN "
        f"latency_ms={int((time.monotonic() - t0) * 1000)}"
    )
    return []


def call_textract_fallback_guarded(
    pdf_input: Union[str, bytes],
    page_number: int,
    document_id: str = "DOC-UNKNOWN",
    document_type: str = "unknown",
) -> List[EvidenceRef]:
    """
    Selective managed OCR path: DetectDocumentText ONLY ($0.0015/page).
    Enforces inviolable hard ceiling: under 100 pages total across runtime.
    core/ never imports boto3; adapter does.
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
        f"Invoked managed Textract DetectDocumentText for page {page_number} "
        f"(Page {_TEXTRACT_PAGES_CONSUMED}/{MAX_TEXTRACT_PAGES})"
    )

    # Offline-safe: counter increments for the spend-guard test, but no network
    # unless explicitly enabled. Keeps CI hermetic.
    if not _textract_enabled():
        return []

    try:
        from adapters.ocr.textract_adapter import detect_text_page
        from core.extraction.native_parser import open_pdf_document, validate_and_clamp_bbox

        doc = open_pdf_document(pdf_input)
        try:
            if page_number > len(doc):
                return []
            page = doc[page_number - 1]
            pw, ph = float(page.rect.width), float(page.rect.height)
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
        finally:
            doc.close()

        lines = detect_text_page(img_bytes)
        evidence: List[EvidenceRef] = []
        for ln in lines:
            text = (ln.get("text") or "").strip()
            if not text:
                continue
            norm = ln.get("bbox_norm") or {}
            x0 = float(norm.get("Left", 0.0)) * pw
            y0 = float(norm.get("Top", 0.0)) * ph
            x1 = x0 + float(norm.get("Width", 0.0)) * pw
            y1 = y0 + float(norm.get("Height", 0.02)) * ph
            bbox = validate_and_clamp_bbox(x0, y0, x1, y1, pw, ph)
            evidence.append(
                EvidenceRef(
                    document_id=document_id,
                    document_type=document_type,
                    page_number=page_number,
                    quoted_span=text,
                    bounding_box=bbox,
                    extraction_method="textract_managed",
                    confidence=max(0.0, min(1.0, float(ln.get("confidence", 0.99)))),
                )
            )
        return evidence
    except Exception as exc:
        logger.warning(f"Textract DetectDocumentText failed for {document_id} p{page_number}: {exc}")
        return []
