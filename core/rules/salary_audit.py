"""
Salary Audit Rule: Reconciles payslip net salary against verified bank payroll credits.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

from decimal import Decimal, InvalidOperation
from typing import Optional, List, Sequence, Union
from core.contracts.facts import MoneyFact
from core.contracts.findings import Finding
from core.contracts.evidence import EvidenceRef


def audit_salary_vs_bank(
    payslip_net: Optional[MoneyFact],
    bank_salary_credit: Optional[Union[MoneyFact, Sequence[MoneyFact]]],
    tolerance: Union[float, Decimal] = 0.05,
) -> Finding:
    """
    RULE-INC-01: Reconciles stated payslip net take-home salary against verified bank credits.
    Pure deterministic financial arithmetic using Decimal. No LLM involvement.

    Semantics:
      - Relative percentage tolerance margin: variance / stated_net <= tolerance.
      - Default tolerance = 0.05 (5.0% relative tolerance per credit policy v1.0).
      - If bank_salary_credit is a sequence, computes the Decimal average across all verified credits.
      - Returns 'unknown' if any required fact is missing, unreadable, zero, negative, or non-numeric.
    """
    # 1. Missing payslip fact
    if payslip_net is None:
        return Finding(
            rule_id="RULE-INC-01",
            rule_name="Salary vs. Bank Credit Reconciliation",
            verdict="unknown",
            reason="Cannot compare: Missing payslip net salary evidence.",
            supporting_evidence=[],
            policy_version="v1.0",
        )

    # 2. Missing or empty bank credits
    if bank_salary_credit is None:
        evidence = [payslip_net.source] if payslip_net and getattr(payslip_net, "source", None) else []
        return Finding(
            rule_id="RULE-INC-01",
            rule_name="Salary vs. Bank Credit Reconciliation",
            verdict="unknown",
            reason="Cannot compare: Missing bank statement salary credit evidence.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    if isinstance(bank_salary_credit, (list, tuple)):
        credits_list = list(bank_salary_credit)
        if len(credits_list) == 0:
            evidence = [payslip_net.source] if payslip_net and getattr(payslip_net, "source", None) else []
            return Finding(
                rule_id="RULE-INC-01",
                rule_name="Salary vs. Bank Credit Reconciliation",
                verdict="unknown",
                reason="Cannot compare: Bank statement salary credits list is empty.",
                supporting_evidence=evidence,
                policy_version="v1.0",
            )
    else:
        credits_list = [bank_salary_credit]

    # 3. Assemble all traceable evidence references
    evidence: List[EvidenceRef] = []
    if getattr(payslip_net, "source", None):
        evidence.append(payslip_net.source)
    for c in credits_list:
        if getattr(c, "source", None):
            evidence.append(c.source)

    # 4. Parse payslip net salary using Decimal
    try:
        stated_amt = getattr(payslip_net, "amount", None)
        if stated_amt is None:
            raise TypeError("Payslip net salary amount is None")
        stated_dec = Decimal(str(stated_amt))
        if stated_dec.is_nan() or stated_dec.is_infinite():
            raise InvalidOperation("Payslip net salary is non-finite")
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return Finding(
            rule_id="RULE-INC-01",
            rule_name="Salary vs. Bank Credit Reconciliation",
            verdict="unknown",
            reason="Cannot compare: Payslip net salary amount is invalid or unreadable.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    if stated_dec <= Decimal("0"):
        return Finding(
            rule_id="RULE-INC-01",
            rule_name="Salary vs. Bank Credit Reconciliation",
            verdict="unknown",
            reason="Cannot compare: Payslip net salary or bank statement credit amount is zero or unavailable.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    # 5. Parse bank credits using Decimal
    bank_decs: List[Decimal] = []
    for idx, c in enumerate(credits_list):
        try:
            c_amt = getattr(c, "amount", None)
            if c_amt is None:
                raise TypeError(f"Bank credit amount at index {idx} is None")
            c_dec = Decimal(str(c_amt))
            if c_dec.is_nan() or c_dec.is_infinite():
                raise InvalidOperation(f"Bank credit at index {idx} is non-finite")
        except (InvalidOperation, TypeError, ValueError, OverflowError):
            return Finding(
                rule_id="RULE-INC-01",
                rule_name="Salary vs. Bank Credit Reconciliation",
                verdict="unknown",
                reason=f"Cannot compare: Bank statement credit at index {idx} has invalid or unreadable amount.",
                supporting_evidence=evidence,
                policy_version="v1.0",
            )

        if c_dec <= Decimal("0"):
            return Finding(
                rule_id="RULE-INC-01",
                rule_name="Salary vs. Bank Credit Reconciliation",
                verdict="unknown",
                reason="Cannot compare: Payslip net salary or bank statement credit amount is zero or unavailable.",
                supporting_evidence=evidence,
                policy_version="v1.0",
            )
        bank_decs.append(c_dec)

    # Average verified bank credit
    avg_bank_dec = sum(bank_decs) / Decimal(str(len(bank_decs)))

    # 6. Parse and validate tolerance threshold
    try:
        tolerance_dec = Decimal(str(tolerance))
        if tolerance_dec < Decimal("0") or tolerance_dec.is_nan() or tolerance_dec.is_infinite():
            raise InvalidOperation("Invalid tolerance value")
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        tolerance_dec = Decimal("0.05")

    # 7. Exact Decimal arithmetic comparison
    variance_dec = abs(stated_dec - avg_bank_dec)
    variance_ratio_dec = variance_dec / stated_dec
    variance_pct = (variance_ratio_dec * Decimal("100")).quantize(Decimal("0.01"))
    tolerance_pct = (tolerance_dec * Decimal("100")).quantize(Decimal("0.1"))

    is_multiple = len(credits_list) > 1
    bank_desc = (
        f"average bank credit ₹{avg_bank_dec:,.2f} (across {len(credits_list)} deposits)"
        if is_multiple
        else f"bank credit ₹{avg_bank_dec:,.2f}"
    )

    if variance_ratio_dec <= tolerance_dec:
        return Finding(
            rule_id="RULE-INC-01",
            rule_name="Salary vs. Bank Credit Reconciliation",
            verdict="pass",
            reason=(
                f"Salary verified: Stated ₹{stated_dec:,.2f} matches {bank_desc} "
                f"within {tolerance_pct:.0f}% tolerance (variance: ₹{variance_dec:,.2f}, {variance_pct}%)."
            ),
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    return Finding(
        rule_id="RULE-INC-01",
        rule_name="Salary vs. Bank Credit Reconciliation",
        verdict="flag",
        reason=(
            f"Salary discrepancy detected: Payslip states ₹{stated_dec:,.2f} but {bank_desc} "
            f"has variance of ₹{variance_dec:,.2f} ({variance_pct}% mismatch vs {tolerance_pct:.1f}% tolerance)."
        ),
        supporting_evidence=evidence,
        policy_version="v1.0",
    )
