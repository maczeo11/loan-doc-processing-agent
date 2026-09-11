"""
Payslip fact extractor.
Owned by Member 3 (Jeevan).

Extracts:
- Employer name
- Employee name
- Gross salary (MoneyFact with EvidenceRef)
- Net salary (MoneyFact with EvidenceRef)
- Total deductions (Optional MoneyFact)
- Pay period string
"""

from typing import List, Dict, Any
from core.extraction.extractors.base import (
    BaseExtractor,
    parse_monetary_amount,
    make_unknown_evidence,
    find_text_match_with_evidence,
)
from core.contracts.facts import PayslipFacts, MoneyFact


class PayslipExtractor(BaseExtractor):
    """Extracts salary, employer, employee, and period metadata from payslip pages."""

    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> PayslipFacts:
        fallback_ev = make_unknown_evidence(doc_id, "payslip")

        # 1. Employee Name
        emp_name, emp_name_ev = find_text_match_with_evidence(
            pages,
            r"(?:Employee\s+Name|Emp\s+Name|Name)\s*[:\-!|]?\s*([A-Za-z .]+)",
            doc_id,
            "payslip",
        )

        # 2. Employer Name
        employer, employer_ev = find_text_match_with_evidence(
            pages,
            r"(?:Employer\s+Name|Employer|Company\s+Name|Company|Organization)\s*[:\-!|]?\s*([A-Za-z0-9 .,&]+)",
            doc_id,
            "payslip",
        )

        # 3. Gross Salary
        gross_val_str, gross_ev = find_text_match_with_evidence(
            pages,
            r"(?:Gross\s+Salary|Gross\s+Pay|Gross\s+Earnings|Total\s+Earnings)\s*[:\-!|]?\s*(?:INR|₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)",
            doc_id,
            "payslip",
        )
        gross_amount = parse_monetary_amount(gross_val_str or "") if gross_val_str else None
        gross_fact = MoneyFact(
            amount=gross_amount if gross_amount is not None else 0.0,
            currency="INR",
            period="monthly",
            basis="gross",
            source=gross_ev if (gross_ev and gross_amount is not None) else fallback_ev,
        )

        # 4. Net Salary
        net_val_str, net_ev = find_text_match_with_evidence(
            pages,
            r"(?:Net\s+Salary|Net\s+Pay|Net\s+Take\s+Home|Take\s+Home\s+Pay|Net\s+Amount)\s*[:\-]?\s*(?:INR|₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)",
            doc_id,
            "payslip",
        )
        net_amount = parse_monetary_amount(net_val_str or "") if net_val_str else None
        net_fact = MoneyFact(
            amount=net_amount if net_amount is not None else 0.0,
            currency="INR",
            period="monthly",
            basis="net",
            source=net_ev if (net_ev and net_amount is not None) else fallback_ev,
        )

        # 5. Total Deductions (Optional)
        ded_val_str, ded_ev = find_text_match_with_evidence(
            pages,
            r"(?:Total\s+Deductions|Deductions\s+Total|Total\s+Deduction)\s*[:\-]?\s*(?:INR|₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)",
            doc_id,
            "payslip",
        )
        ded_amount = parse_monetary_amount(ded_val_str or "") if ded_val_str else None
        deductions_fact = None
        if ded_amount is not None and ded_ev:
            deductions_fact = MoneyFact(
                amount=ded_amount,
                currency="INR",
                period="monthly",
                basis="deduction",
                source=ded_ev,
            )

        # 6. Pay Period String
        period_str, _ = find_text_match_with_evidence(
            pages,
            r"(?:Pay\s+Period|For\s+the\s+month\s+of|Month)\s*[:\-]?\s*([A-Za-z0-9 ,-]+)",
            doc_id,
            "payslip",
        )

        return PayslipFacts(
            employee_name=emp_name or "UNKNOWN",
            employer_name=employer or "UNKNOWN",
            gross_salary=gross_fact,
            net_salary=net_fact,
            deductions_total=deductions_fact,
            pay_period_str=period_str,
        )
