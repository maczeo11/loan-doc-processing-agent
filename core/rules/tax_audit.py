"""
Tax Audit Rule: Reconciles ITR-V Gross Total Income against annual stated earnings.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

from decimal import Decimal, InvalidOperation
from typing import List, Optional, Union

from core.contracts.evidence import EvidenceRef
from core.contracts.facts import MoneyFact
from core.contracts.findings import Finding

# AGENTS.md RULE-TAX-01: annualised payslip gross vs ITR gross, tolerance <= 0.10.
# Wider than RULE-INC-01's 0.05 because ITR gross total income legitimately
# includes non-salary heads (interest, rent) absent from a payslip.
TAX_TOLERANCE = 0.10


def audit_tax_vs_income(
    stated_annual_income: Optional[MoneyFact] = None,
    itr_gross_income: Optional[MoneyFact] = None,
    tolerance: Union[float, Decimal] = TAX_TOLERANCE,
    *,
    is_monthly: Optional[bool] = None,
    monthly_gross: Optional[MoneyFact] = None,
    stated_income: Optional[MoneyFact] = None,
) -> Finding:
    """
    RULE-TAX-01: Reconciles ITR-V Gross Total Income against annualized payslip gross income
    (calculated deterministically as monthly gross × 12).
    Pure deterministic financial arithmetic using Decimal. No LLM involvement.

    Semantics:
      - Relative variance ratio: |annualized_stated - itr_gross| / annualized_stated <= tolerance.
      - Tolerance defaults to 0.10 (10.0% relative tolerance margin).
      - Strict semantic separation: Gross Total Income only; never confuses net salary,
        taxable deductions, or tax paid.
      - If required values are missing, unreadable, zero, negative, or non-finite, returns 'unknown'.
    """
    # 1. Resolve payslip fact from available parameters
    payslip_fact = (
        monthly_gross
        if monthly_gross is not None
        else (stated_annual_income if stated_annual_income is not None else stated_income)
    )

    # 2. Assemble evidence references
    evidence: List[EvidenceRef] = []
    if payslip_fact and getattr(payslip_fact, "source", None):
        evidence.append(payslip_fact.source)
    if itr_gross_income and getattr(itr_gross_income, "source", None):
        evidence.append(itr_gross_income.source)

    # 3. Check for missing required inputs
    if payslip_fact is None or itr_gross_income is None:
        missing_items: List[str] = []
        if payslip_fact is None:
            missing_items.append("monthly payslip gross income")
        if itr_gross_income is None:
            missing_items.append("ITR-V gross total income")

        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason=f"Missing stated annual income or ITR-V filing data (missing {', '.join(missing_items)}).",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    # 4. Parse ITR gross income using Decimal
    try:
        itr_amt = getattr(itr_gross_income, "amount", None)
        if itr_amt is None:
            raise TypeError("ITR gross total income amount is None")
        itr_dec = Decimal(str(itr_amt))
        if itr_dec.is_nan() or itr_dec.is_infinite():
            raise InvalidOperation("ITR gross total income is non-finite")
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason="Cannot compare: ITR gross total income amount is invalid, non-finite, or unreadable.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    if itr_dec <= Decimal("0"):
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason="Cannot compare: Annual stated income or ITR gross income amount is zero or unavailable.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    # 5. Parse stated / payslip gross income using Decimal
    try:
        raw_amt = getattr(payslip_fact, "amount", None)
        if raw_amt is None:
            raise TypeError("Stated gross income amount is None")
        raw_dec = Decimal(str(raw_amt))
        if raw_dec.is_nan() or raw_dec.is_infinite():
            raise InvalidOperation("Stated gross income is non-finite")
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason="Cannot compare: Stated monthly/annual gross income amount is invalid, non-finite, or unreadable.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    if raw_dec <= Decimal("0"):
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="unknown",
            reason=f"Cannot compute variance: annualised payslip gross is {raw_dec:,.2f}.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    # 6. Determine whether to annualize (monthly gross × 12)
    if monthly_gross is not None or is_monthly is True:
        multiply_by_12 = True
    elif stated_annual_income is not None and is_monthly is None:
        # If explicitly passed via stated_annual_income without is_monthly flag:
        # Check if period is explicitly 'annual' or if stated_annual_income parameter was used
        if getattr(payslip_fact, "period", None) == "annual":
            multiply_by_12 = False
        elif getattr(payslip_fact, "period", None) == "monthly":
            multiply_by_12 = True
        else:
            # Check ratio: if raw_dec * 12 is much closer to itr_dec than raw_dec alone
            var_as_monthly = abs((raw_dec * Decimal("12")) - itr_dec)
            var_as_annual = abs(raw_dec - itr_dec)
            multiply_by_12 = var_as_monthly < var_as_annual
    elif getattr(payslip_fact, "period", None) == "annual" or is_monthly is False:
        multiply_by_12 = False
    elif getattr(payslip_fact, "period", None) == "monthly":
        multiply_by_12 = True
    else:
        var_as_monthly = abs((raw_dec * Decimal("12")) - itr_dec)
        var_as_annual = abs(raw_dec - itr_dec)
        multiply_by_12 = var_as_monthly < var_as_annual

    if multiply_by_12:
        monthly_dec = raw_dec
        annualized_dec = raw_dec * Decimal("12")
        calc_str = (
            f"Annualized stated income ₹{annualized_dec:,.2f} "
            f"(calculated as 12 × monthly gross ₹{monthly_dec:,.2f})"
        )
    else:
        annualized_dec = raw_dec
        calc_str = f"Annualized stated income ₹{annualized_dec:,.2f}"

    # 7. Parse and validate tolerance threshold
    try:
        tolerance_dec = Decimal(str(tolerance))
        if tolerance_dec < Decimal("0") or tolerance_dec.is_nan() or tolerance_dec.is_infinite():
            raise InvalidOperation("Invalid tolerance value")
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        tolerance_dec = Decimal(str(TAX_TOLERANCE))

    # 8. Exact Decimal variance calculation
    variance_dec = abs(annualized_dec - itr_dec)
    variance_ratio_dec = variance_dec / annualized_dec
    variance_pct = (variance_ratio_dec * Decimal("100")).quantize(Decimal("0.1"))
    tolerance_pct = (tolerance_dec * Decimal("100")).quantize(Decimal("0.1"))

    if variance_ratio_dec <= tolerance_dec:
        return Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="pass",
            reason=(
                f"Tax return verified: {calc_str} reconciles with "
                f"ITR gross total income ₹{itr_dec:,.2f} within {tolerance_pct:.0f}% tolerance "
                f"({variance_pct}% variance)."
            ),
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    direction = "under-reports" if itr_dec < annualized_dec else "over-reports"
    return Finding(
        rule_id="RULE-TAX-01",
        rule_name="ITR Gross Income Reconciliation",
        verdict="flag",
        reason=(
            f"Tax return discrepancy: ITR {direction} against payslip evidence. "
            f"{calc_str} is ₹{annualized_dec:,.2f} but "
            f"ITR gross total income is ₹{itr_dec:,.2f} ({variance_pct}% mismatch, "
            f"exceeds {tolerance_pct:.0f}% threshold)."
        ),
        supporting_evidence=evidence,
        policy_version="v1.0",
    )
