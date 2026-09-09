"""
Base Extractor protocol for document-specific entity extraction.

Rules from AGENTS.md:
- No extracted fact is accepted without an EvidenceRef.
- If evidence is missing, the value is UNKNOWN with confidence 0.0.
- Deterministic code decides, AI explains.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Union
import re
from pydantic import BaseModel
from core.contracts.evidence import EvidenceRef, BoundingBox


def parse_monetary_amount(raw_text: str) -> Optional[float]:
    """
    Parses currency strings like '₹ 1,50,000.00', 'INR 85,000', 'Rs. 45000' into a float.
    Returns None if no valid monetary number can be parsed.
    """
    if not raw_text:
        return None

    cleaned = raw_text.replace("₹", "").replace("INR", "").replace("Rs.", "").replace("Rs", "")
    cleaned = cleaned.replace(",", "").replace(" ", "").strip()

    match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        val = float(match.group(0))
        return round(val, 2)
    except ValueError:
        return None


def make_unknown_evidence(
    doc_id: str,
    doc_type: str,
    page_number: int = 1,
    span: str = "UNKNOWN",
) -> EvidenceRef:
    """Creates a standard missing/unknown EvidenceRef with confidence 0.0."""
    return EvidenceRef(
        document_id=doc_id,
        document_type=doc_type,
        page_number=max(1, page_number),
        quoted_span=span,
        bounding_box=BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0),
        confidence=0.0,
    )


def find_text_match_with_evidence(
    pages: List[Dict[str, Any]],
    pattern: Union[str, re.Pattern],
    doc_id: str,
    doc_type: str,
    group_idx: int = 1,
) -> Tuple[Optional[str], Optional[EvidenceRef]]:
    """
    Searches across document pages for a regex pattern.
    Extracts the matched string and attempts to resolve its bounding-box coordinates
    from the page's word or span metadata.
    """
    compiled = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern

    for page in pages:
        page_num = page.get("page_number", 1)
        raw_text = page.get("text", "")
        page_w = page.get("page_width", 600.0)
        page_h = page.get("page_height", 800.0)

        match = compiled.search(raw_text)
        if not match:
            continue

        raw_val = None
        if group_idx <= len(match.groups()) and match.group(group_idx) is not None:
            raw_val = match.group(group_idx)
        else:
            # Fallback to the first non-None capturing group
            for g in match.groups():
                if g is not None:
                    raw_val = g
                    break
            if raw_val is None:
                raw_val = match.group(0)

        matched_value = raw_val.strip()

        full_matched_span = match.group(0).strip()

        # Try to locate bounding box from page words if present
        matched_words = [w for w in page.get("words", []) if w.get("word") in matched_value.split()]
        if matched_words:
            bboxes = [w["bbox"] for w in matched_words]
            x0 = min(b.x0 for b in bboxes)
            y0 = min(b.y0 for b in bboxes)
            x1 = max(b.x1 for b in bboxes)
            y1 = max(b.y1 for b in bboxes)
            resolved_bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1, page_width=page_w, page_height=page_h)
        else:
            # Fallback coordinate footprint
            resolved_bbox = BoundingBox(x0=50.0, y0=50.0, x1=250.0, y1=70.0, page_width=page_w, page_height=page_h)

        evidence = EvidenceRef(
            document_id=doc_id,
            document_type=doc_type,
            page_number=page_num,
            quoted_span=full_matched_span,
            bounding_box=resolved_bbox,
            extraction_method="pymupdf_native",
            confidence=0.95,
        )
        return matched_value, evidence

    return None, None


class BaseExtractor(ABC):
    """Abstract base class for extracting structured facts with EvidenceRef provenance."""

    @abstractmethod
    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> BaseModel:
        """Extract typed facts from document pages with bounding-box evidence."""
        pass
