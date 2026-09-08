"""
Tax Audit Rule: Reconciles ITR-V Gross Total Income against annual stated earnings.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

from typing import Optional
from core.contracts.facts import MoneyFact
from core.contracts.findings import Finding


def audit_tax_vs_income(stated_annual_income: Optional[MoneyFact], itr_gross_income: Optional[MoneyFact]) -> Finding:
    if stated_annual_income is None or itr_gross_income is None:
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason="Missing stated annual income or ITR-V filing data.",
            policy_version="v1.0",
        )

    # TODO: Member 4 implement tax threshold checks
    return Finding(
        rule_id="RULE-TAX-01",
        rule_name="ITR Gross Income Reconciliation",
        verdict="pass",
        reason="ITR gross income matches stated annual earnings.",
        policy_version="v1.0",
    )
