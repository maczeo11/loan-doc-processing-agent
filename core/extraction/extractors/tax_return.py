"""
Tax return (ITR acknowledgement) fact extractor.
Owned by Member 3 (Jeevan).

Extracts:
- Assessee name
- PAN number
- Assessment year (e.g. 2024-25)
- Gross total income (MoneyFact with EvidenceRef)
- Total tax paid (Optional MoneyFact with EvidenceRef)
"""

from typing import List, Dict, Any
from core.extraction.extractors.base import (
    BaseExtractor,
    parse_monetary_amount,
    make_unknown_evidence,
    find_text_match_with_evidence,
)
from core.contracts.facts import TaxReturnFacts, MoneyFact


class TaxReturnExtractor(BaseExtractor):
    """Extracts gross annual income, assessment year, and tax payments from tax filings."""

    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> TaxReturnFacts:
        fallback_ev = make_unknown_evidence(doc_id, "tax_acknowledgement")

        # 1. Assessee Name
        name, _ = find_text_match_with_evidence(
            pages,
            r"(?:Name\s+of\s+Assessee|Assessee\s+Name|Name|Taxpayer\s+Name)\s*[:\-]\s*([A-Za-z .]+)",
            doc_id,
            "tax_acknowledgement",
        )

        # 2. PAN Number
        pan, pan_ev = find_text_match_with_evidence(
            pages,
            r"\b([A-Z]{5}[0-9]{4}[A-Z])\b",
            doc_id,
            "tax_acknowledgement",
        )

        # 3. Assessment Year
        ay_str, _ = find_text_match_with_evidence(
            pages,
            r"(?:Assessment\s+Year|AY|A\.Y\.)\s*[:\-]?\s*(20\d{2}[-\s/]\d{2,4})",
            doc_id,
            "tax_acknowledgement",
        )

        # 4. Gross Total Income
        income_str, income_ev = find_text_match_with_evidence(
            pages,
            r"(?:Gross\s+Total\s+Income|Total\s+Income|Gross\s+Income)\s*[:\-]?\s*(?:INR|₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)",
            doc_id,
            "tax_acknowledgement",
        )
        gross_income_amt = parse_monetary_amount(income_str or "") if income_str else None
        gross_income_fact = MoneyFact(
            amount=gross_income_amt if gross_income_amt is not None else 0.0,
            currency="INR",
            period="annual",
            basis="gross",
            source=income_ev if (income_ev and gross_income_amt is not None) else fallback_ev,
        )

        # 5. Total Tax Paid (Optional)
        tax_str, tax_ev = find_text_match_with_evidence(
            pages,
            r"(?:Total\s+Tax\s+Paid|Tax\s+Paid|Taxes\s+Paid)\s*[:\-]?\s*(?:INR|₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)",
            doc_id,
            "tax_acknowledgement",
        )
        total_tax_amt = parse_monetary_amount(tax_str or "") if tax_str else None
        total_tax_fact = None
        if total_tax_amt is not None and tax_ev:
            total_tax_fact = MoneyFact(
                amount=total_tax_amt,
                currency="INR",
                period="annual",
                basis="deduction",
                source=tax_ev,
            )

        return TaxReturnFacts(
            assessee_name=name or "UNKNOWN",
            pan_number=pan or "UNKNOWN",
            assessment_year=ay_str or "UNKNOWN",
            gross_total_income=gross_income_fact,
            total_tax_paid=total_tax_fact,
        )
