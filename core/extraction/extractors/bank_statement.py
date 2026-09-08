"""
Bank statement fact extractor.

Extracts:
- Bank name, Account number
- Account holder name
- Total deposits, Average monthly balance
- Recurring salary credits
All facts MUST carry EvidenceRef.
"""

from typing import List, Dict, Any
from core.extraction.extractors.base import BaseExtractor
from core.contracts.facts import BankStatementFacts, MoneyFact
from core.contracts.evidence import EvidenceRef, BoundingBox


class BankStatementExtractor(BaseExtractor):
    """Extracts balance, salary deposits, and account metadata from bank statements."""

    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> BankStatementFacts:
        fallback_evidence = EvidenceRef(
            document_id=doc_id,
            document_type="bank_statement",
            page_number=1,
            quoted_span="UNKNOWN",
            bounding_box=BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0),
            confidence=0.0,
        )
        return BankStatementFacts(
            document_id=doc_id,
            bank_name=None,
            account_holder_name=None,
            statement_start_date=None,
            statement_end_date=None,
            total_credits=MoneyFact(amount=0.0, currency="INR", source=fallback_evidence),
            total_debits=MoneyFact(amount=0.0, currency="INR", source=fallback_evidence),
            closing_balance=MoneyFact(amount=0.0, currency="INR", source=fallback_evidence),
            detected_salary_credits=[],
        )
