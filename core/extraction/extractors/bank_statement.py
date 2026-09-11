"""
Bank statement fact extractor.
Owned by Member 3 (Jeevan).

Extracts:
- Account holder name
- Bank name
- Account number (masked to last 4 digits)
- Recurring salary credits (List of MoneyFact with EvidenceRef)
- Average salary credit (computed deterministically)
- Closing balance (MoneyFact with EvidenceRef)
- Bounced transaction count
"""

import re
from typing import List, Dict, Any
from core.extraction.extractors.base import (
    BaseExtractor,
    parse_monetary_amount,
    find_text_match_with_evidence,
)
from core.contracts.facts import BankStatementFacts, MoneyFact
from core.contracts.evidence import EvidenceRef, BoundingBox


class BankStatementExtractor(BaseExtractor):
    """Extracts balance, salary deposits, and account metadata from bank statements."""

    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> BankStatementFacts:
        # 1. Account Holder
        holder_name, _ = find_text_match_with_evidence(
            pages,
            r"(?:Account\s+Holder|Customer\s+Name|Account\s+Name|Name)\s*[:\-!|]?\s*([A-Za-z .]+)",
            doc_id,
            "bank_statement",
        )

        # 2. Bank Name
        bank_name, _ = find_text_match_with_evidence(
            pages,
            r"(?:Bank\s+Name\s*[:\-!|]?\s*([A-Za-z .]+)|(HDFC\s+Bank|ICICI\s+Bank|State\s+Bank\s+of\s+India|SBI|Axis\s+Bank|Kotak\s+Mahindra\s+Bank|Punjab\s+National\s+Bank))",
            doc_id,
            "bank_statement",
        )

        # 3. Account Number (Masked)
        raw_acct, _ = find_text_match_with_evidence(
            pages,
            r"(?:Account\s+No|Account\s+Number|A/C\s+No|Acct\s+No)\.?\s*[:\-]?\s*([X\d\-]{6,20})",
            doc_id,
            "bank_statement",
        )
        if raw_acct:
            digits_only = re.sub(r"\D", "", raw_acct)
            if len(digits_only) >= 4:
                masked_acct = f"XXXXXX{digits_only[-4:]}"
            else:
                masked_acct = raw_acct
        else:
            masked_acct = "XXXXXX0000"

        # 4. Closing Balance
        balance_str, bal_ev = find_text_match_with_evidence(
            pages,
            r"(?:Closing\s+Balance|Available\s+Balance|Account\s+Balance|Net\s+Balance)\s*[:\-]?\s*(?:INR|₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)",
            doc_id,
            "bank_statement",
        )
        closing_bal_fact = None
        if balance_str and bal_ev:
            bal_amt = parse_monetary_amount(balance_str)
            if bal_amt is not None:
                closing_bal_fact = MoneyFact(
                    amount=bal_amt,
                    currency="INR",
                    period="one_time",
                    basis="balance",
                    source=bal_ev,
                )

        # 5. Salary Credits & Bounces across all transaction lines
        salary_credits: List[MoneyFact] = []
        bounced_count = 0

        salary_pattern = re.compile(
            r"(?:SALARY|SAL\s+CR|PAYROLL|DIRECT\s+DEP|NEFT.*SALARY|SALARY\s+CREDIT)[^\n\r]*?(?:INR|₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        )
        bounce_pattern = re.compile(
            r"\b(?:BOUNCE|RETURN|INSUFFICIENT\s+FUNDS|ECS\s+RETURN|CHQ\s+RTN)\b",
            re.IGNORECASE,
        )

        for page in pages:
            text = page.get("text", "")
            page_num = page.get("page_number", 1)
            page_w = page.get("page_width", 600.0)
            page_h = page.get("page_height", 800.0)

            # Count bounces per transaction line
            for line in text.splitlines():
                if bounce_pattern.search(line):
                    bounced_count += 1

            # Find salary credit transactions
            for match in salary_pattern.finditer(text):
                amt_str = match.group(1)
                parsed_amt = parse_monetary_amount(amt_str)
                if parsed_amt is not None and parsed_amt > 0:
                    span_text = match.group(0).strip()
                    ev = EvidenceRef(
                        document_id=doc_id,
                        document_type="bank_statement",
                        page_number=page_num,
                        quoted_span=span_text,
                        bounding_box=BoundingBox(
                            x0=50.0, y0=200.0, x1=500.0, y1=220.0, page_width=page_w, page_height=page_h
                        ),
                        extraction_method="pymupdf_native",
                        confidence=0.95,
                    )
                    salary_credits.append(
                        MoneyFact(
                            amount=parsed_amt,
                            currency="INR",
                            period="monthly",
                            basis="net",
                            source=ev,
                        )
                    )

        # 6. Average Salary Credit
        avg_salary_credit = None
        if salary_credits:
            avg_amount = round(sum(c.amount for c in salary_credits) / len(salary_credits), 2)
            avg_salary_credit = MoneyFact(
                amount=avg_amount,
                currency="INR",
                period="monthly",
                basis="net",
                source=salary_credits[0].source,
            )

        return BankStatementFacts(
            account_holder=holder_name or "UNKNOWN",
            bank_name=bank_name or "UNKNOWN",
            account_number_masked=masked_acct,
            salary_credits=salary_credits,
            average_salary_credit=avg_salary_credit,
            closing_balance=closing_bal_fact,
            bounced_transactions=bounced_count,
        )
