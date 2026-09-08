"""
Salary Audit Rule: Reconciles payslip net salary against verified bank payroll credits.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

from typing import Optional
from core.contracts.facts import MoneyFact
from core.contracts.findings import Finding


def audit_salary_vs_bank(payslip_net: Optional[MoneyFact], bank_salary_credit: Optional[MoneyFact], tolerance: float = 0.10) -> Finding:
    """
    Compares stated net take-home salary against recurring deposits in bank statement.
    If either value is missing, verdict MUST be 'unknown'.
    """
    if payslip_net is None or bank_salary_credit is None:
        return Finding(
            rule_id="RULE-INC-01",
            rule_name="Salary vs. Bank Credit Reconciliation",
            verdict="unknown",
            reason="Cannot compare: Missing payslip net salary or bank statement credit evidence.",
            policy_version="v1.0",
        )

    variance = abs(payslip_net.amount - bank_salary_credit.amount)
    variance_ratio = variance / (payslip_net.amount + 1e-6)

    if variance_ratio <= tolerance:
        return Finding(
            rule_id="RULE-INC-01",
            rule_name="Salary vs. Bank Credit Reconciliation",
            verdict="pass",
            reason=f"Salary verified: Stated ₹{payslip_net.amount:,.2f} matches bank credit ₹{bank_salary_credit.amount:,.2f} within {tolerance*100:.0f}% tolerance.",
            supporting_evidence=[payslip_net.source, bank_salary_credit.source],
            policy_version="v1.0",
        )

    return Finding(
        rule_id="RULE-INC-01",
        rule_name="Salary vs. Bank Credit Reconciliation",
        verdict="flag",
        reason=f"Salary discrepancy detected: Payslip states ₹{payslip_net.amount:,.2f} but bank credit is ₹{bank_salary_credit.amount:,.2f} ({variance_ratio*100:.1f}% mismatch).",
        supporting_evidence=[payslip_net.source, bank_salary_credit.source],
        policy_version="v1.0",
    )
