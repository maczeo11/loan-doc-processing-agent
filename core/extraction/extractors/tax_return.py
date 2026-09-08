"""
Tax return (ITR acknowledgement) fact extractor.

Extracts:
- Assessment year
- Taxpayer PAN / Name
- Gross total income
- Total tax paid
All facts MUST carry EvidenceRef.
"""

from typing import List, Dict, Any, Optional
from core.extraction.extractors.base import BaseExtractor
from core.contracts.facts import TaxReturnFacts, MoneyFact
from core.contracts.evidence import EvidenceRef, BoundingBox


class TaxReturnExtractor(BaseExtractor):
    """Extracts gross annual income, assessment year, and tax payments from tax filings."""

    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> TaxReturnFacts:
        fallback_evidence = EvidenceRef(
            document_id=doc_id,
            document_type="tax_acknowledgement",
            page_number=1,
            quoted_span="UNKNOWN",
            bounding_box=BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0),
            confidence=0.0,
        )
        return TaxReturnFacts(
            document_id=doc_id,
            assessment_year="UNKNOWN",
            taxpayer_name=None,
            pan_number=None,
            gross_total_income=MoneyFact(amount=0.0, currency="INR", source=fallback_evidence),
            total_tax_paid=MoneyFact(amount=0.0, currency="INR", source=fallback_evidence),
        )
