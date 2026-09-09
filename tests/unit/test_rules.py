"""
Unit tests for deterministic financial and completeness rules.
Human-authored assertions ensuring money and completeness logic behaves deterministically.
"""

from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import ApplicantFact, MoneyFact
from core.rules.bank_arithmetic import validate_bank_statement_arithmetic
from core.rules.completeness import evaluate_completeness
from core.rules.identity import (
    audit_identity_consistency,
    compute_name_similarity,
    normalize_name_tokens,
)
from core.rules.salary_audit import audit_salary_vs_bank
from core.rules.tax_audit import audit_tax_vs_income


def make_dummy_evidence(doc_id: str, text: str) -> EvidenceRef:
    return EvidenceRef(
        document_id=doc_id,
        document_type="payslip",
        page_number=1,
        quoted_span=text,
        bounding_box=BoundingBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0),
        confidence=1.0,
    )


def test_completeness_all_present():
    required = ["application_form", "payslip", "bank_statement", "tax_acknowledgement", "id_card"]
    uploaded = ["application_form", "payslip", "bank_statement", "tax_acknowledgement", "id_card"]
    finding = evaluate_completeness(uploaded, required)
    assert finding.verdict == "pass"


def test_completeness_missing_tax():
    required = ["application_form", "payslip", "bank_statement", "tax_acknowledgement", "id_card"]
    uploaded = ["application_form", "payslip", "bank_statement", "id_card"]
    finding = evaluate_completeness(uploaded, required)
    assert finding.verdict == "flag"
    assert "tax_acknowledgement" in finding.reason


def test_salary_reconciliation_exact_match():
    ev_pay = make_dummy_evidence("DOC-PAY", "50000")
    ev_bank = make_dummy_evidence("DOC-BANK", "50000")

    payslip_net = MoneyFact(amount=50000, currency="INR", source=ev_pay)
    bank_credit = MoneyFact(amount=50000, currency="INR", source=ev_bank)

    finding = audit_salary_vs_bank(payslip_net, bank_credit, tolerance=0.05)
    assert finding.verdict == "pass"


def test_salary_reconciliation_missing_bank_returns_unknown():
    ev_pay = make_dummy_evidence("DOC-PAY", "50000")
    payslip_net = MoneyFact(amount=50000, currency="INR", source=ev_pay)

    finding = audit_salary_vs_bank(payslip_net, None)
    assert finding.verdict == "unknown"


# ==============================================================================
# Additional Salary Audit Edge-Case Tests (RULE-INC-01)
# ==============================================================================

def test_salary_reconciliation_within_5_percent_default_tolerance():
    ev_pay = make_dummy_evidence("DOC-PAY", "100000")
    ev_bank = make_dummy_evidence("DOC-BANK", "96000")

    payslip_net = MoneyFact(amount=100000, currency="INR", source=ev_pay)
    bank_credit = MoneyFact(amount=96000, currency="INR", source=ev_bank)  # 4.0% discrepancy

    finding = audit_salary_vs_bank(payslip_net, bank_credit)  # Uses default tolerance=0.05
    assert finding.verdict == "pass"
    assert "Salary verified" in finding.reason
    assert len(finding.supporting_evidence) == 2


def test_salary_reconciliation_exceeding_5_percent_tolerance():
    ev_pay = make_dummy_evidence("DOC-PAY", "100000")
    ev_bank = make_dummy_evidence("DOC-BANK", "85000")

    payslip_net = MoneyFact(amount=100000, currency="INR", source=ev_pay)
    bank_credit = MoneyFact(amount=85000, currency="INR", source=ev_bank)  # 15.0% discrepancy

    finding = audit_salary_vs_bank(payslip_net, bank_credit)
    assert finding.verdict == "flag"
    assert "Salary discrepancy detected" in finding.reason
    assert len(finding.supporting_evidence) == 2


def test_salary_reconciliation_zero_or_negative_amount_returns_unknown():
    ev_pay = make_dummy_evidence("DOC-PAY", "0")
    ev_bank = make_dummy_evidence("DOC-BANK", "50000")

    payslip_net = MoneyFact(amount=0, currency="INR", source=ev_pay)
    bank_credit = MoneyFact(amount=50000, currency="INR", source=ev_bank)

    finding = audit_salary_vs_bank(payslip_net, bank_credit)
    assert finding.verdict == "unknown"
    assert "zero or unavailable" in finding.reason


# ==============================================================================
# Tax Audit Tests (RULE-TAX-01)
# ==============================================================================


def test_tax_audit_exact_match():
    ev_pay = make_dummy_evidence("DOC-PAY", "1200000")
    ev_tax = make_dummy_evidence("DOC-TAX", "1200000")

    stated_annual = MoneyFact(amount=1200000, currency="INR", source=ev_pay)
    itr_gross = MoneyFact(amount=1200000, currency="INR", source=ev_tax)

    finding = audit_tax_vs_income(stated_annual, itr_gross)
    assert finding.rule_id == "RULE-TAX-01"
    assert finding.verdict == "pass"
    assert "Tax return verified" in finding.reason
    assert len(finding.supporting_evidence) == 2
    assert finding.supporting_evidence[0].document_id == "DOC-PAY"
    assert finding.supporting_evidence[1].document_id == "DOC-TAX"


def test_tax_audit_within_5_percent_tolerance():
    ev_pay = make_dummy_evidence("DOC-PAY", "1200000")
    ev_tax = make_dummy_evidence("DOC-TAX", "1240000")

    stated_annual = MoneyFact(amount=1200000, currency="INR", source=ev_pay)
    itr_gross = MoneyFact(amount=1240000, currency="INR", source=ev_tax)  # 3.33% variance

    finding = audit_tax_vs_income(stated_annual, itr_gross)
    assert finding.verdict == "pass"
    assert "Tax return verified" in finding.reason


def test_tax_audit_exceeding_5_percent_discrepancy():
    ev_pay = make_dummy_evidence("DOC-PAY", "1200000")
    ev_tax = make_dummy_evidence("DOC-TAX", "1500000")

    stated_annual = MoneyFact(amount=1200000, currency="INR", source=ev_pay)
    itr_gross = MoneyFact(amount=1500000, currency="INR", source=ev_tax)  # 25% variance

    finding = audit_tax_vs_income(stated_annual, itr_gross)
    assert finding.verdict == "flag"
    assert "Tax return discrepancy" in finding.reason
    assert "25.0% mismatch" in finding.reason
    assert len(finding.supporting_evidence) == 2


def test_tax_audit_missing_facts_returns_unknown():
    ev_pay = make_dummy_evidence("DOC-PAY", "1200000")
    stated_annual = MoneyFact(amount=1200000, currency="INR", source=ev_pay)

    # Missing ITR
    f1 = audit_tax_vs_income(stated_annual, None)
    assert f1.verdict == "unknown"
    assert "Missing stated annual income or ITR-V" in f1.reason

    # Missing Stated
    ev_tax = make_dummy_evidence("DOC-TAX", "1200000")
    itr_gross = MoneyFact(amount=1200000, currency="INR", source=ev_tax)
    f2 = audit_tax_vs_income(None, itr_gross)
    assert f2.verdict == "unknown"


def test_tax_audit_zero_amount_returns_unknown():
    ev_pay = make_dummy_evidence("DOC-PAY", "0")
    ev_tax = make_dummy_evidence("DOC-TAX", "1200000")

    stated_annual = MoneyFact(amount=0, currency="INR", source=ev_pay)
    itr_gross = MoneyFact(amount=1200000, currency="INR", source=ev_tax)

    finding = audit_tax_vs_income(stated_annual, itr_gross)
    assert finding.verdict == "unknown"
    assert "zero or unavailable" in finding.reason


# ==============================================================================
# Identity Consistency Tests (RULE-ID-01)
# ==============================================================================


def make_applicant(name: str, pan: str = "ABCDE1234F") -> ApplicantFact:
    ev_name = make_dummy_evidence("DOC-KYC", name)
    ev_pan = make_dummy_evidence("DOC-KYC", pan)
    return ApplicantFact(
        full_name=name,
        source_name=ev_name,
        pan_number=pan,
        source_pan=ev_pan,
    )


def test_identity_token_normalization_and_similarity():
    # Exact match
    assert normalize_name_tokens("Aarav Sharma") == "aarav sharma"
    assert compute_name_similarity("Aarav Sharma", "Aarav Sharma") == 1.0

    # Word order invariance
    assert normalize_name_tokens("Sharma, Aarav") == "aarav sharma"
    assert compute_name_similarity("Sharma, Aarav", "Aarav Sharma") == 1.0

    # Middle initial (minor variation >= 85%)
    sim_initial = compute_name_similarity("Sneha R Kulkarni", "Sneha Kulkarni")
    assert sim_initial >= 0.85

    # Maiden / different name (< 70%)
    sim_different = compute_name_similarity("Sneha Joshi", "Sneha Kulkarni")
    assert sim_different < 0.70


def test_identity_consistency_exact_match():
    applicant = make_applicant("Bhanu Teja")
    finding = audit_identity_consistency(applicant, payslip_name="Bhanu Teja", bank_name="Bhanu Teja")

    assert finding.rule_id == "RULE-ID-01"
    assert finding.verdict == "pass"
    assert "Identity confirmed" in finding.reason
    assert len(finding.supporting_evidence) >= 1
    assert finding.supporting_evidence[0].document_id == "DOC-KYC"


def test_identity_consistency_reordered_name_passes():
    applicant = make_applicant("Aarav Sharma")
    finding = audit_identity_consistency(applicant, payslip_name="Sharma Aarav", bank_name="Aarav Sharma")

    assert finding.verdict == "pass"
    assert "Identity confirmed" in finding.reason


def test_identity_consistency_minor_initial_passes():
    applicant = make_applicant("Sneha R Kulkarni")
    finding = audit_identity_consistency(applicant, payslip_name="Sneha Kulkarni", bank_name="Sneha R Kulkarni")

    assert finding.verdict == "pass"


def test_identity_consistency_minor_variation_flags_for_review():
    applicant = make_applicant("Aarav Sharma")
    # Fuzzy score ~72.7% falls into [70%, 84%] threshold
    finding = audit_identity_consistency(applicant, payslip_name="Mohammed Aarav Sharma", bank_name="Aarav Sharma")

    assert finding.verdict == "flag"
    assert "Reviewer verification required for name variation" in finding.reason


def test_identity_consistency_critical_mismatch_flags():
    applicant = make_applicant("Sneha Kulkarni")
    finding = audit_identity_consistency(applicant, payslip_name="Sneha Joshi", bank_name="Sneha Kulkarni")

    assert finding.verdict == "flag"
    assert "Critical identity mismatch" in finding.reason


def test_identity_consistency_pan_mismatch_flags():
    applicant = make_applicant("Bhanu Teja", pan="ABCDE1234F")
    # Name matches, but PAN differs
    finding = audit_identity_consistency(
        applicant,
        payslip_name="Bhanu Teja",
        bank_name="Bhanu Teja",
        pan_to_compare="XYZAB9999K",
    )

    assert finding.verdict == "flag"
    assert "PAN 'ABCDE1234F' does not match document PAN 'XYZAB9999K'" in finding.reason


def test_identity_consistency_missing_applicant_returns_unknown():
    finding = audit_identity_consistency(None, payslip_name="Bhanu Teja", bank_name="Bhanu Teja")
    assert finding.verdict == "unknown"
    assert "Missing primary applicant KYC" in finding.reason


def test_identity_consistency_unknown_applicant_name_returns_unknown():
    applicant = make_applicant("UNKNOWN")
    finding = audit_identity_consistency(applicant, payslip_name="Bhanu Teja", bank_name="Bhanu Teja")
    assert finding.verdict == "unknown"
    assert "missing readable full name" in finding.reason


def test_identity_consistency_missing_doc_names_returns_unknown():
    applicant = make_applicant("Bhanu Teja")
    finding = audit_identity_consistency(applicant, payslip_name=None, bank_name=None)
    assert finding.verdict == "unknown"
    assert "missing or unknown" in finding.reason


# ==============================================================================
# Bank Statement Arithmetic Validation Tests (RULE-BANK-01)
# ==============================================================================


def test_bank_arithmetic_exact_match_passes():
    ev_open = make_dummy_evidence("DOC-BANK", "10000.00")
    ev_cred = make_dummy_evidence("DOC-BANK", "5000.00")
    ev_deb = make_dummy_evidence("DOC-BANK", "2000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "13000.00")

    open_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_open)
    cred_fact = MoneyFact(amount=5000.00, currency="INR", basis="net", source=ev_cred)
    deb_fact = MoneyFact(amount=2000.00, currency="INR", basis="deduction", source=ev_deb)
    close_fact = MoneyFact(amount=13000.00, currency="INR", basis="balance", source=ev_close)

    finding = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=cred_fact,
        debits=deb_fact,
    )

    assert finding.rule_id == "RULE-BANK-01"
    assert finding.verdict == "pass"
    assert "Bank statement arithmetic verified" in finding.reason
    assert "Opening ₹10,000.00 + Total Credits ₹5,000.00 - Total Debits ₹2,000.00 = Calculated Closing ₹13,000.00" in finding.reason
    assert len(finding.supporting_evidence) == 4


def test_bank_arithmetic_mismatch_flags():
    ev_open = make_dummy_evidence("DOC-BANK", "10000.00")
    ev_cred = make_dummy_evidence("DOC-BANK", "5000.00")
    ev_deb = make_dummy_evidence("DOC-BANK", "2000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "12000.00")

    open_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_open)
    cred_fact = MoneyFact(amount=5000.00, currency="INR", basis="net", source=ev_cred)
    deb_fact = MoneyFact(amount=2000.00, currency="INR", basis="deduction", source=ev_deb)
    # Stated closing 12,000 vs calculated 13,000 (variance ₹1,000 > 0.05)
    close_fact = MoneyFact(amount=12000.00, currency="INR", basis="balance", source=ev_close)

    finding = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=cred_fact,
        debits=deb_fact,
    )

    assert finding.rule_id == "RULE-BANK-01"
    assert finding.verdict == "flag"
    assert "Bank statement arithmetic discrepancy" in finding.reason
    assert "differs from stated closing balance ₹12,000.00 by ₹1,000.00" in finding.reason
    assert len(finding.supporting_evidence) == 4


def test_bank_arithmetic_multiple_credits_and_debits_passes():
    ev_open = make_dummy_evidence("DOC-BANK", "25000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "42500.00")

    open_fact = MoneyFact(amount=25000.00, currency="INR", basis="balance", source=ev_open)
    close_fact = MoneyFact(amount=42500.00, currency="INR", basis="balance", source=ev_close)

    credits = [
        MoneyFact(amount=30000.00, currency="INR", source=make_dummy_evidence("DOC-BANK", "30000")),
        MoneyFact(amount=5000.00, currency="INR", source=make_dummy_evidence("DOC-BANK", "5000")),
        MoneyFact(amount=2500.00, currency="INR", source=make_dummy_evidence("DOC-BANK", "2500")),
    ]  # Sum = 37,500.00

    debits = [
        MoneyFact(amount=12000.00, currency="INR", source=make_dummy_evidence("DOC-BANK", "12000")),
        MoneyFact(amount=8000.00, currency="INR", source=make_dummy_evidence("DOC-BANK", "8000")),
    ]  # Sum = 20,000.00

    # 25,000 + 37,500 - 20,000 = 42,500.00
    finding = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=credits,
        debits=debits,
    )

    assert finding.verdict == "pass"
    assert "Total Credits ₹37,500.00 (3 items)" in finding.reason
    assert "Total Debits ₹20,000.00 (2 items)" in finding.reason
    assert len(finding.supporting_evidence) == 7


def test_bank_arithmetic_zero_transactions_opening_equals_closing():
    ev_open = make_dummy_evidence("DOC-BANK", "15000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "15000.00")

    open_fact = MoneyFact(amount=15000.00, currency="INR", basis="balance", source=ev_open)
    close_fact = MoneyFact(amount=15000.00, currency="INR", basis="balance", source=ev_close)

    # Zero transactions when opening equals closing -> PASS
    f_pass = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=[],
        debits=[],
    )
    assert f_pass.verdict == "pass"
    assert "Total Credits ₹0.00" in f_pass.reason
    assert "Total Debits ₹0.00" in f_pass.reason

    # Zero transactions when opening differs from closing -> FLAG
    diff_close = MoneyFact(amount=14000.00, currency="INR", basis="balance", source=ev_close)
    f_flag = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=diff_close,
        credits=[],
        debits=[],
    )
    assert f_flag.verdict == "flag"
    assert "differs from stated closing balance ₹14,000.00 by ₹1,000.00" in f_flag.reason


def test_bank_arithmetic_missing_opening_balance_returns_unknown():
    ev_close = make_dummy_evidence("DOC-BANK", "10000.00")
    close_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_close)

    finding = validate_bank_statement_arithmetic(
        opening_balance=None,
        closing_balance=close_fact,
        credits=[],
        debits=[],
    )
    assert finding.verdict == "unknown"
    assert "Missing or unreadable opening balance" in finding.reason


def test_bank_arithmetic_missing_closing_balance_returns_unknown():
    ev_open = make_dummy_evidence("DOC-BANK", "10000.00")
    open_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_open)

    finding = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=None,
        credits=[],
        debits=[],
    )
    assert finding.verdict == "unknown"
    assert "Missing or unreadable closing balance" in finding.reason


def test_bank_arithmetic_missing_transaction_amount_returns_unknown():
    ev_open = make_dummy_evidence("DOC-BANK", "10000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "15000.00")
    open_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_open)
    close_fact = MoneyFact(amount=15000.00, currency="INR", basis="balance", source=ev_close)

    # Credit with missing/None amount
    bad_credit = {"amount": None, "source": make_dummy_evidence("DOC-BANK", "missing")}

    finding = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=[bad_credit],
        debits=[],
    )
    assert finding.verdict == "unknown"
    assert "Credit transaction #1 amount is missing or unknown" in finding.reason


def test_bank_arithmetic_invalid_transaction_amount_returns_unknown():
    ev_open = make_dummy_evidence("DOC-BANK", "10000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "15000.00")
    open_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_open)
    close_fact = MoneyFact(amount=15000.00, currency="INR", basis="balance", source=ev_close)

    # Malformed non-numeric transaction
    bad_credit = {"amount": "not_a_number", "source": make_dummy_evidence("DOC-BANK", "bad")}
    f1 = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=[bad_credit],
        debits=[],
    )
    assert f1.verdict == "unknown"
    assert "Credit transaction #1 amount is invalid, non-finite, or negative" in f1.reason

    # Negative transaction amount
    negative_debit = {"amount": -250.00, "source": make_dummy_evidence("DOC-BANK", "-250")}
    f2 = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=[],
        debits=[negative_debit],
    )
    assert f2.verdict == "unknown"
    assert "Debit transaction #1 amount is invalid, non-finite, or negative" in f2.reason


def test_bank_arithmetic_rounding_tolerance_boundary():
    ev = make_dummy_evidence("DOC-BANK", "test")
    # Opening 1000.00 + Credits 250.33 - Debits 100.28 = 1150.05
    open_fact = MoneyFact(amount=1000.00, currency="INR", basis="balance", source=ev)
    cred_fact = MoneyFact(amount=250.33, currency="INR", source=ev)
    deb_fact = MoneyFact(amount=100.28, currency="INR", source=ev)

    # 1. Exactly at tolerance boundary (0.05 discrepancy -> PASS)
    # Stated closing 1150.10 vs calculated 1150.05 (variance = 0.05)
    close_at_boundary = MoneyFact(amount=1150.10, currency="INR", basis="balance", source=ev)
    f_bound = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_at_boundary,
        credits=cred_fact,
        debits=deb_fact,
        tolerance=0.05,
    )
    assert f_bound.verdict == "pass"
    assert "variance: ₹0.05" in f_bound.reason

    # 2. Exceeding tolerance boundary (0.06 discrepancy -> FLAG)
    # Stated closing 1150.11 vs calculated 1150.05 (variance = 0.06 > 0.05)
    close_exceeding = MoneyFact(amount=1150.11, currency="INR", basis="balance", source=ev)
    f_exceed = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_exceeding,
        credits=cred_fact,
        debits=deb_fact,
        tolerance=0.05,
    )
    assert f_exceed.verdict == "flag"
    assert "by ₹0.06 (exceeds ₹0.05 tolerance)" in f_exceed.reason

    # 3. Custom tolerance (e.g. 0.10 allows 0.06 -> PASS)
    f_custom = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_exceeding,
        credits=cred_fact,
        debits=deb_fact,
        tolerance=0.10,
    )
    assert f_custom.verdict == "pass"
