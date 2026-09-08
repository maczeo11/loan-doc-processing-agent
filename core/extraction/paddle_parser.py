"""
CPU-based PaddleOCR parser for scanned pages with no native text layer.
Owned by Member 3 (Jeevan).

Invariants & Guarantees:
- Runs strictly on CPU (no GPU requirement).
- Lazy-loads PaddleOCR so test environments and native-only setups stay fast and resilient.
- Normalizes pixel-space OCR coordinates back into PDF point space (BoundingBox).
- Validates and clamps all extracted coordinates against page dimensions.
"""

import logging
from typing import List, Union, Optional
import io
import fitz
from core.contracts.evidence import EvidenceRef
from core.extraction.native_parser import open_pdf_document, validate_and_clamp_bbox

logger = logging.getLogger(__name__)

# Global cache for lazy initialized CPU OCR engine
_PADDLE_OCR_INSTANCE = None


def get_paddle_ocr_engine():
    """
    Lazily initializes the PaddleOCR CPU engine singleton.
    Returns None if paddleocr is not installed.
    """
    global _PADDLE_OCR_INSTANCE
    if _PADDLE_OCR_INSTANCE is not None:
        return _PADDLE_OCR_INSTANCE

    try:
        from paddleocr import PaddleOCR
        # Initialize PaddleOCR on CPU only
        _PADDLE_OCR_INSTANCE = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False)
        return _PADDLE_OCR_INSTANCE
    except ImportError:
        logger.warning("PaddleOCR is not installed in the current environment. Scanned page OCR is unavailable.")
        return None
    except Exception as e:
        logger.warning(f"Could not initialize PaddleOCR CPU engine: {e}")
        return None


def extract_scanned_text_with_ocr(
    pdf_input: Union[str, bytes],
    page_number: int,
    document_id: str = "DOC-UNKNOWN",
    document_type: str = "unknown",
    dpi: int = 150,
) -> List[EvidenceRef]:
    """
    Renders a 1-indexed PDF page to an image pixmap and runs PaddleOCR on CPU.
    Translates pixel bounding boxes back to PDF point dimensions.
    """
    if page_number < 1:
        raise ValueError(f"Page numbers must be 1-indexed (got {page_number})")

    doc = open_pdf_document(pdf_input)
    try:
        if page_number > len(doc):
            return []

        page = doc[page_number - 1]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        ocr_engine = get_paddle_ocr_engine()
        if ocr_engine is None:
            return []

        # Render PDF page to image pixmap
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        pix_w, pix_h = pix.width, pix.height

        # Scale factor from pixel coordinates to PDF point coordinates
        scale_x = page_width / float(pix_w) if pix_w > 0 else 1.0
        scale_y = page_height / float(pix_h) if pix_h > 0 else 1.0

        # Execute OCR inference
        results = ocr_engine.ocr(img_bytes, cls=True)
        if not results or not results[0]:
            return []

        evidence_items: List[EvidenceRef] = []
        for line in results[0]:
            # line format: [ [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], (text, confidence) ]
            box_points = line[0]
            text, conf = line[1]

            cleaned_text = str(text).strip()
            if not cleaned_text:
                continue

            x_coords = [pt[0] for pt in box_points]
            y_coords = [pt[1] for pt in box_points]

            raw_x0 = min(x_coords) * scale_x
            raw_x1 = max(x_coords) * scale_x
            raw_y0 = min(y_coords) * scale_y
            raw_y1 = max(y_coords) * scale_y

            bbox = validate_and_clamp_bbox(
                x0=raw_x0,
                y0=raw_y0,
                x1=raw_x1,
                y1=raw_y1,
                page_width=page_width,
                page_height=page_height,
            )

            evidence_items.append(
                EvidenceRef(
                    document_id=document_id,
                    document_type=document_type,
                    page_number=page_number,
                    quoted_span=cleaned_text,
                    bounding_box=bbox,
                    extraction_method="paddleocr_cpu",
                    confidence=round(float(conf), 4),
                )
            )

        return evidence_items
    finally:
        doc.close()
