"""
Tax Audit Rule: Reconciles ITR-V Gross Total Income against annual stated earnings.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

from typing import Optional, List
from core.contracts.facts import MoneyFact
from core.contracts.findings import Finding
from core.contracts.evidence import EvidenceRef


def audit_tax_vs_income(
    stated_annual_income: Optional[MoneyFact],
    itr_gross_income: Optional[MoneyFact],
    tolerance: float = 0.05,
) -> Finding:
    """
    RULE-TAX-01: Reconciles stated annual earnings (or annualized monthly gross salary)
    against ITR-V Gross Total Income.
    Tolerance: 5.0% (0.05).
    Missing, unreadable, or non-positive values result in 'unknown'.
    """
    if stated_annual_income is None or itr_gross_income is None:
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason="Missing stated annual income or ITR-V filing data.",
            supporting_evidence=[],
            policy_version="v1.0",
        )

    # Check for non-positive or unreadable values
    if stated_annual_income.amount <= 0 or itr_gross_income.amount <= 0:
        evidence: List[EvidenceRef] = []
        if stated_annual_income.source:
            evidence.append(stated_annual_income.source)
        if itr_gross_income.source:
            evidence.append(itr_gross_income.source)
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason="Cannot compare: Annual stated income or ITR gross income amount is zero or unavailable.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    evidence = [stated_annual_income.source, itr_gross_income.source]
    stated_amt = stated_annual_income.amount
    itr_amt = itr_gross_income.amount

    variance = abs(stated_amt - itr_amt)
    variance_ratio = variance / (stated_amt + 1e-6)

    if variance_ratio <= tolerance:
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="pass",
            reason=(
                f"Tax return verified: Annualized stated income ₹{stated_amt:,.2f} reconciles with "
                f"ITR gross total income ₹{itr_amt:,.2f} within {tolerance * 100:.0f}% tolerance "
                f"({variance_ratio * 100:.1f}% variance)."
            ),
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    return Finding(
        rule_id="RULE-TAX-01",
        rule_name="ITR Gross Income Reconciliation",
        verdict="flag",
        reason=(
            f"Tax return discrepancy: Annualized stated income is ₹{stated_amt:,.2f} but "
            f"ITR gross total income is ₹{itr_amt:,.2f} ({variance_ratio * 100:.1f}% mismatch, "
            f"exceeds {tolerance * 100:.0f}% threshold)."
        ),
        supporting_evidence=evidence,
        policy_version="v1.0",
    )
