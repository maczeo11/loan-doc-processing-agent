"""
Tax Audit Rule: Reconciles ITR-V Gross Total Income against annual stated earnings.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

from typing import Optional
from core.contracts.facts import MoneyFact
from core.contracts.findings import Finding

# AGENTS.md RULE-TAX-01: annualised payslip gross vs ITR gross, tolerance <= 0.10.
# Wider than RULE-INC-01's 0.05 because ITR gross total income legitimately
# includes non-salary heads (interest, rent) absent from a payslip.
TAX_TOLERANCE = 0.10


def audit_tax_vs_income(stated_annual_income: Optional[MoneyFact], itr_gross_income: Optional[MoneyFact], tolerance: float = TAX_TOLERANCE) -> Finding:
    """
    Compares annualised payslip gross income against ITR-V gross total income.

    The caller is responsible for annualising monthly payslip gross (12 x monthly)
    before invoking this rule; both arguments are treated as annual figures.
    If either value is missing, verdict MUST be 'unknown'.
    """
    if stated_annual_income is None or itr_gross_income is None:
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason="Missing stated annual income or ITR-V filing data.",
            policy_version="v1.0",
        )

    # A non-positive base makes the variance ratio meaningless; abstain rather than guess.
    if stated_annual_income.amount <= 0:
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason=f"Cannot compute variance: annualised payslip gross is {stated_annual_income.amount:,.2f}.",
            supporting_evidence=[stated_annual_income.source, itr_gross_income.source],
            policy_version="v1.0",
        )

    evidence = [stated_annual_income.source, itr_gross_income.source]
    variance = abs(stated_annual_income.amount - itr_gross_income.amount)
    variance_ratio = variance / stated_annual_income.amount

    if variance_ratio <= tolerance:
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="pass",
            reason=(
                f"ITR gross total income ₹{itr_gross_income.amount:,.2f} reconciles with "
                f"annualised payslip gross ₹{stated_annual_income.amount:,.2f} "
                f"({variance_ratio*100:.1f}% variance, within {tolerance*100:.0f}% tolerance)."
            ),
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    direction = "under-reports" if itr_gross_income.amount < stated_annual_income.amount else "over-reports"
    return Finding(
        rule_id="RULE-TAX-01",
        rule_name="ITR Gross Income Reconciliation",
        verdict="flag",
        reason=(
            f"Income discrepancy: ITR {direction} against payslip evidence. "
            f"ITR gross total income ₹{itr_gross_income.amount:,.2f} vs annualised payslip gross "
            f"₹{stated_annual_income.amount:,.2f} ({variance_ratio*100:.1f}% variance, "
            f"exceeds {tolerance*100:.0f}% tolerance)."
        ),
        supporting_evidence=evidence,
        policy_version="v1.0",
    )
