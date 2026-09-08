"""
Identity proof fact extractor (PAN / Aadhaar / Passport).

Extracts:
- Full Name
- ID Number (PAN, Aadhaar last 4, etc.)
- Date of Birth
All facts MUST carry EvidenceRef.
"""

from typing import List, Dict, Any, Optional
from core.extraction.extractors.base import BaseExtractor
from core.contracts.facts import ApplicantFact
from core.contracts.evidence import EvidenceRef, BoundingBox


class IdCardExtractor(BaseExtractor):
    """Extracts KYC applicant identity and document identifiers."""

    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> ApplicantFact:
        fallback_evidence = EvidenceRef(
            document_id=doc_id,
            document_type="id_card",
            page_number=1,
            quoted_span="UNKNOWN",
            bounding_box=BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0),
            confidence=0.0,
        )
        return ApplicantFact(
            full_name="UNKNOWN",
            pan=None,
            dob=None,
            source=fallback_evidence,
        )
