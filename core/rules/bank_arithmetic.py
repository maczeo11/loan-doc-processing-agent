"""
Bank Statement Arithmetic Validation Rule (RULE-BANK-01).
HUMAN-ONLY ZONE: Owned by Member 4 (Sravanthi).

Verifies the fundamental bank statement balance equation:
  Opening Balance + Total Credits - Total Debits = Closing Balance

Invariants:
  1. Deterministic Python only — zero LLM involvement in financial arithmetic.
  2. Floating-point immunity: Uses Decimal arithmetic with explicit string conversions.
  3. Explicit tolerance: Absolute difference |stated_closing - calculated_closing| <= tolerance (default 0.05).
  4. Invariant provenance: All calculations grounded with EvidenceRef citations when available.
  5. Missing or invalid values strictly return 'unknown', never a guessed pass or coerced zero.
  6. Zero transactions: If no transactions occur, opening balance must equal closing balance.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, List, Optional, Sequence, Tuple, Union

from core.contracts.evidence import EvidenceRef
from core.contracts.facts import MoneyFact
from core.contracts.findings import Finding


def _parse_amount_and_evidence(
    item: Any,
    field_name: str,
    allow_negative: bool = True,
) -> Tuple[Optional[Decimal], Optional[EvidenceRef], Optional[str]]:
    """
    Deterministically parses an amount and its evidence citation from various input types.

    Returns:
      (amount_decimal, evidence_ref, error_type)
      error_type is None if valid, 'missing' if absent/unknown, or 'invalid' if malformed.
    """
    if item is None:
        return None, None, "missing"

    evidence: Optional[EvidenceRef] = None
    raw_amount: Any = None

    # Handle MoneyFact instance
    if isinstance(item, MoneyFact):
        raw_amount = item.amount
        evidence = item.source
    # Handle dict with amount/source
    elif isinstance(item, dict):
        raw_amount = item.get("amount")
        evidence = item.get("source")
    # Handle objects with amount attribute
    elif hasattr(item, "amount"):
        raw_amount = getattr(item, "amount")
        evidence = getattr(item, "source", None)
    # Direct numeric or Decimal input
    else:
        raw_amount = item

    if raw_amount is None:
        return None, evidence, "missing"

    # Check string representations for 'unknown' or empty
    if isinstance(raw_amount, str):
        cleaned = raw_amount.strip().lower()
        if not cleaned or cleaned in ("unknown", "none", "null", "n/a"):
            return None, evidence, "missing"

    # Parse using Decimal
    try:
        dec = Decimal(str(raw_amount))
        if dec.is_nan() or dec.is_infinite():
            return None, evidence, "invalid"
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return None, evidence, "invalid"

    # Disallow negative transactions (credits/debits represent positive flow magnitudes)
    if not allow_negative and dec < Decimal("0"):
        return None, evidence, "invalid"

    return dec, evidence, None


def validate_bank_statement_arithmetic(
    opening_balance: Optional[Union[MoneyFact, Decimal, float, int, dict]],
    closing_balance: Optional[Union[MoneyFact, Decimal, float, int, dict]],
    credits: Optional[Union[MoneyFact, Sequence[Union[MoneyFact, Decimal, float, int, dict]], Decimal, float, int, dict]] = None,
    debits: Optional[Union[MoneyFact, Sequence[Union[MoneyFact, Decimal, float, int, dict]], Decimal, float, int, dict]] = None,
    *,
    total_credits: Optional[Union[MoneyFact, Decimal, float, int, dict]] = None,
    total_debits: Optional[Union[MoneyFact, Decimal, float, int, dict]] = None,
    tolerance: Union[float, Decimal, str] = 0.05,
) -> Finding:
    """
    RULE-BANK-01: Verifies that Opening Balance + Total Credits - Total Debits = Closing Balance.

    Parameters:
      opening_balance: Stated opening balance (MoneyFact, Decimal, float, or dict).
      closing_balance: Stated closing balance (MoneyFact, Decimal, float, or dict).
      credits: Sequence of credit transactions, or single credit MoneyFact.
      debits: Sequence of debit transactions, or single debit MoneyFact.
      total_credits: Optional direct total credits override.
      total_debits: Optional direct total debits override.
      tolerance: Allowed arithmetic variance threshold (defaults to 0.05 currency units).

    Returns:
      Finding contract with rule_id='RULE-BANK-01', verdict ('pass' | 'flag' | 'unknown'),
      and human-auditable mathematical explanation.
    """
    all_evidence: List[EvidenceRef] = []

    # 1. Parse Opening Balance
    open_dec, open_ev, open_err = _parse_amount_and_evidence(opening_balance, "Opening Balance", allow_negative=True)
    if open_ev:
        all_evidence.append(open_ev)

    if open_err == "missing":
        return Finding(
            rule_id="RULE-BANK-01",
            rule_name="Bank Statement Arithmetic Validation",
            verdict="unknown",
            reason="Cannot validate bank statement arithmetic: Missing or unreadable opening balance.",
            supporting_evidence=all_evidence,
            policy_version="v1.0",
        )
    if open_err == "invalid":
        return Finding(
            rule_id="RULE-BANK-01",
            rule_name="Bank Statement Arithmetic Validation",
            verdict="unknown",
            reason="Cannot validate bank statement arithmetic: Opening balance amount is invalid, non-finite, or malformed.",
            supporting_evidence=all_evidence,
            policy_version="v1.0",
        )

    # 2. Parse Closing Balance
    close_dec, close_ev, close_err = _parse_amount_and_evidence(closing_balance, "Closing Balance", allow_negative=True)
    if close_ev:
        all_evidence.append(close_ev)

    if close_err == "missing":
        return Finding(
            rule_id="RULE-BANK-01",
            rule_name="Bank Statement Arithmetic Validation",
            verdict="unknown",
            reason="Cannot validate bank statement arithmetic: Missing or unreadable closing balance.",
            supporting_evidence=all_evidence,
            policy_version="v1.0",
        )
    if close_err == "invalid":
        return Finding(
            rule_id="RULE-BANK-01",
            rule_name="Bank Statement Arithmetic Validation",
            verdict="unknown",
            reason="Cannot validate bank statement arithmetic: Closing balance amount is invalid, non-finite, or malformed.",
            supporting_evidence=all_evidence,
            policy_version="v1.0",
        )

    # 3. Process Credits
    credits_list: List[Any] = []
    if total_credits is not None:
        credits_list = [total_credits]
    elif credits is not None:
        if isinstance(credits, (list, tuple)):
            credits_list = list(credits)
        else:
            credits_list = [credits]

    total_credits_dec = Decimal("0")
    for idx, c in enumerate(credits_list):
        c_dec, c_ev, c_err = _parse_amount_and_evidence(c, f"Credit Transaction #{idx + 1}", allow_negative=False)
        if c_ev:
            all_evidence.append(c_ev)
        if c_err == "missing":
            return Finding(
                rule_id="RULE-BANK-01",
                rule_name="Bank Statement Arithmetic Validation",
                verdict="unknown",
                reason=f"Cannot validate bank statement arithmetic: Credit transaction #{idx + 1} amount is missing or unknown.",
                supporting_evidence=all_evidence,
                policy_version="v1.0",
            )
        if c_err == "invalid":
            return Finding(
                rule_id="RULE-BANK-01",
                rule_name="Bank Statement Arithmetic Validation",
                verdict="unknown",
                reason=f"Cannot validate bank statement arithmetic: Credit transaction #{idx + 1} amount is invalid, non-finite, or negative.",
                supporting_evidence=all_evidence,
                policy_version="v1.0",
            )
        total_credits_dec += c_dec  # type: ignore[operator]

    # 4. Process Debits
    debits_list: List[Any] = []
    if total_debits is not None:
        debits_list = [total_debits]
    elif debits is not None:
        if isinstance(debits, (list, tuple)):
            debits_list = list(debits)
        else:
            debits_list = [debits]

    total_debits_dec = Decimal("0")
    for idx, d in enumerate(debits_list):
        d_dec, d_ev, d_err = _parse_amount_and_evidence(d, f"Debit Transaction #{idx + 1}", allow_negative=False)
        if d_ev:
            all_evidence.append(d_ev)
        if d_err == "missing":
            return Finding(
                rule_id="RULE-BANK-01",
                rule_name="Bank Statement Arithmetic Validation",
                verdict="unknown",
                reason=f"Cannot validate bank statement arithmetic: Debit transaction #{idx + 1} amount is missing or unknown.",
                supporting_evidence=all_evidence,
                policy_version="v1.0",
            )
        if d_err == "invalid":
            return Finding(
                rule_id="RULE-BANK-01",
                rule_name="Bank Statement Arithmetic Validation",
                verdict="unknown",
                reason=f"Cannot validate bank statement arithmetic: Debit transaction #{idx + 1} amount is invalid, non-finite, or negative.",
                supporting_evidence=all_evidence,
                policy_version="v1.0",
            )
        total_debits_dec += d_dec  # type: ignore[operator]

    # 5. Parse and Validate Tolerance
    try:
        tolerance_dec = Decimal(str(tolerance))
        if tolerance_dec < Decimal("0") or tolerance_dec.is_nan() or tolerance_dec.is_infinite():
            raise InvalidOperation("Tolerance must be non-negative and finite")
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        tolerance_dec = Decimal("0.05")

    # 6. Execute Deterministic Balance Equation
    # Calculated Closing = Opening Balance + Total Credits - Total Debits
    calc_closing_dec = open_dec + total_credits_dec - total_debits_dec  # type: ignore[operator]
    variance_dec = abs(close_dec - calc_closing_dec)  # type: ignore[operator]

    num_credits = len(credits_list)
    num_debits = len(debits_list)
    credits_desc = (
        f"Total Credits ₹{total_credits_dec:,.2f} ({num_credits} item{'s' if num_credits != 1 else ''})"
        if num_credits > 1
        else f"Total Credits ₹{total_credits_dec:,.2f}"
    )
    debits_desc = (
        f"Total Debits ₹{total_debits_dec:,.2f} ({num_debits} item{'s' if num_debits != 1 else ''})"
        if num_debits > 1
        else f"Total Debits ₹{total_debits_dec:,.2f}"
    )

    calc_formula = (
        f"Opening ₹{open_dec:,.2f} + {credits_desc} - {debits_desc} = "
        f"Calculated Closing ₹{calc_closing_dec:,.2f}"
    )

    # 7. Evaluate Verdict
    if variance_dec <= tolerance_dec:
        return Finding(
            rule_id="RULE-BANK-01",
            rule_name="Bank Statement Arithmetic Validation",
            verdict="pass",
            reason=(
                f"Bank statement arithmetic verified: {calc_formula} reconciles with stated "
                f"closing balance ₹{close_dec:,.2f} within ₹{tolerance_dec} tolerance "
                f"(variance: ₹{variance_dec:,.2f})."
            ),
            supporting_evidence=all_evidence,
            policy_version="v1.0",
        )

    return Finding(
        rule_id="RULE-BANK-01",
        rule_name="Bank Statement Arithmetic Validation",
        verdict="flag",
        reason=(
            f"Bank statement arithmetic discrepancy: {calc_formula} differs from stated "
            f"closing balance ₹{close_dec:,.2f} by ₹{variance_dec:,.2f} "
            f"(exceeds ₹{tolerance_dec} tolerance)."
        ),
        supporting_evidence=all_evidence,
        policy_version="v1.0",
    )


# Aliases for flexible integration
audit_bank_statement_arithmetic = validate_bank_statement_arithmetic
audit_bank_arithmetic = validate_bank_statement_arithmetic
