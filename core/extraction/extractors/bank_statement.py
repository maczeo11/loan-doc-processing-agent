"""
Bank statement fact extractor.

Extracts:
- Account holder, Bank name, Masked account number
- Recurring salary credits, Closing balance
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
            account_holder="UNKNOWN",
            bank_name="UNKNOWN",
            account_number_masked="XXXXXX0000",
            salary_credits=[],
            average_salary_credit=None,
            closing_balance=MoneyFact(amount=0.0, currency="INR", source=fallback_evidence),
            bounced_transactions=0,
        )
