"""
Payslip fact extractor.

Extracts:
- Employer name
- Employee name
- Gross salary, Net salary
- Pay period / date
All facts MUST carry EvidenceRef.
"""

from typing import List, Dict, Any
from core.extraction.extractors.base import BaseExtractor
from core.contracts.facts import PayslipFacts, MoneyFact
from core.contracts.evidence import EvidenceRef, BoundingBox


class PayslipExtractor(BaseExtractor):
    """Extracts salary, employer, and dates from payslip pages."""

    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> PayslipFacts:
        # Jeevan to implement regex/layout extraction with word coordinates
        fallback_evidence = EvidenceRef(
            document_id=doc_id,
            document_type="payslip",
            page_number=1,
            quoted_span="UNKNOWN",
            bounding_box=BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0),
            confidence=0.0,
        )
        return PayslipFacts(
            document_id=doc_id,
            employer_name=None,
            employee_name=None,
            gross_salary=MoneyFact(amount=0.0, currency="INR", source=fallback_evidence),
            net_salary=MoneyFact(amount=0.0, currency="INR", source=fallback_evidence),
            pay_period=None,
        )
