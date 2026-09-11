"""
Unit tests for deterministic financial and completeness rules.
Human-authored assertions ensuring money and completeness logic behaves deterministically.
"""

from core.contracts.evidence import BoundingBox, EvidenceRef
from core.contracts.facts import ApplicantFact, MoneyFact
from core.rules.bank_arithmetic import validate_bank_statement_arithmetic
from core.rules.completeness import evaluate_completeness
from core.rules.identity import audit_identity_consistency
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


def test_salary_reconciliation_within_5_percent_default_tolerance():
    ev_pay = make_dummy_evidence("DOC-PAY", "100000.00")
    ev_bank = make_dummy_evidence("DOC-BANK", "97000.00")

    payslip_net = MoneyFact(amount=100000.00, currency="INR", source=ev_pay)
    bank_credit = MoneyFact(amount=97000.00, currency="INR", source=ev_bank)

    # 3% variance <= 5% default tolerance -> PASS
    finding = audit_salary_vs_bank(payslip_net, bank_credit)
    assert finding.verdict == "pass"
    assert "Salary verified" in finding.reason


def test_salary_reconciliation_exceeding_5_percent_tolerance():
    ev_pay = make_dummy_evidence("DOC-PAY", "100000.00")
    ev_bank = make_dummy_evidence("DOC-BANK", "90000.00")

    payslip_net = MoneyFact(amount=100000.00, currency="INR", source=ev_pay)
    bank_credit = MoneyFact(amount=90000.00, currency="INR", source=ev_bank)

    # 10% variance > 5% default tolerance -> FLAG
    finding = audit_salary_vs_bank(payslip_net, bank_credit)
    assert finding.verdict == "flag"
    assert "Salary discrepancy detected" in finding.reason


def test_salary_reconciliation_zero_or_negative_amount_returns_unknown():
    ev_pay = make_dummy_evidence("DOC-PAY", "0.00")
    ev_bank = make_dummy_evidence("DOC-BANK", "50000.00")

    payslip_zero = MoneyFact(amount=0.00, currency="INR", source=ev_pay)
    bank_credit = MoneyFact(amount=50000.00, currency="INR", source=ev_bank)

    finding = audit_salary_vs_bank(payslip_zero, bank_credit)
    assert finding.verdict == "unknown"


# ── RULE-TAX-01: ITR Gross Income Reconciliation ──────────────────────────────


def make_annual_gross(amount: float) -> MoneyFact:
    ev = make_dummy_evidence("DOC-PAY", str(amount))
    return MoneyFact(amount=amount, currency="INR", period="annual", basis="gross", source=ev)


def make_itr_gross(amount: float) -> MoneyFact:
    ev = make_dummy_evidence("DOC-ITR", str(amount))
    return MoneyFact(amount=amount, currency="INR", period="annual", basis="gross", source=ev)


def test_tax_audit_within_tolerance_passes():
    # 12 x 50,000 = 600,000 annualised vs ITR 620,000 -> 3.3% variance.
    finding = audit_tax_vs_income(make_annual_gross(600000), make_itr_gross(620000))
    assert finding.verdict == "pass"
    assert len(finding.supporting_evidence) == 2


def test_tax_audit_at_tolerance_boundary_passes():
    # Exactly 10% variance must pass (tolerance is inclusive).
    finding = audit_tax_vs_income(make_annual_gross(600000), make_itr_gross(540000))
    assert finding.verdict == "pass"


def test_tax_audit_under_reported_income_flags():
    # ITR declares 400,000 against 600,000 of payslip evidence -> 33% variance.
    finding = audit_tax_vs_income(make_annual_gross(600000), make_itr_gross(400000))
    assert finding.verdict == "flag"
    assert "under-reports" in finding.reason


def test_tax_audit_over_reported_income_flags():
    finding = audit_tax_vs_income(make_annual_gross(600000), make_itr_gross(900000))
    assert finding.verdict == "flag"
    assert "over-reports" in finding.reason


def test_tax_audit_missing_itr_returns_unknown():
    assert audit_tax_vs_income(make_annual_gross(600000), None).verdict == "unknown"
    assert audit_tax_vs_income(None, make_itr_gross(600000)).verdict == "unknown"


def test_tax_audit_zero_income_abstains_instead_of_guessing():
    # Never divide by zero and never guess a 'pass' from a meaningless ratio.
    finding = audit_tax_vs_income(make_annual_gross(0), make_itr_gross(600000))
    assert finding.verdict == "unknown"


# ── RULE-ID-01: Cross-Document Identity Consistency ───────────────────────────


def make_applicant(name: str, pan: str = "ABCDE1234F") -> ApplicantFact:
    return ApplicantFact(
        full_name=name,
        source_name=make_dummy_evidence("DOC-KYC", name),
        pan_number=pan,
        source_pan=make_dummy_evidence("DOC-KYC", pan),
    )


def test_identity_exact_match_passes():
    finding = audit_identity_consistency(make_applicant("Rajesh Kumar Sharma"), "Rajesh Kumar Sharma", "Rajesh Kumar Sharma")
    assert finding.verdict == "pass"


def test_identity_reordered_tokens_pass_via_token_sort():
    # token_sort_ratio must not flag pure word-order variation between documents.
    finding = audit_identity_consistency(make_applicant("Rajesh Kumar Sharma"), "Sharma Rajesh Kumar", "RAJESH KUMAR SHARMA")
    assert finding.verdict == "pass"


def test_identity_different_person_flags():
    finding = audit_identity_consistency(make_applicant("Rajesh Kumar Sharma"), "Priya Venkatesan", None)
    assert finding.verdict == "flag"
    assert "payslip" in finding.reason


def test_identity_flag_cites_both_compared_documents():
    """Regression: a cross-document mismatch must cite the compared document's
    own page, not KYC twice (same-doc evidence illusion)."""
    finding = audit_identity_consistency(
        make_applicant("Sneha Kulkarni"),
        "Sneha Joshi",
        None,
        payslip_name_evidence=make_dummy_evidence("DOC-PAY-01", "Employee Name: Sneha Joshi"),
    )
    assert finding.verdict == "flag"
    assert "Sneha Joshi" in finding.reason
    doc_ids = {ev.document_id for ev in finding.supporting_evidence}
    assert "DOC-KYC" in doc_ids
    assert "DOC-PAY-01" in doc_ids


def test_identity_pass_cites_compared_document_pages():
    """A pass must also carry both sides so the reviewer can click through."""
    finding = audit_identity_consistency(
        make_applicant("Rajesh Kumar Sharma"),
        "Rajesh Kumar Sharma",
        None,
        payslip_name_evidence=make_dummy_evidence("DOC-PAY-01", "Employee Name: Rajesh Kumar Sharma"),
    )
    assert finding.verdict == "pass"
    doc_ids = {ev.document_id for ev in finding.supporting_evidence}
    assert {"DOC-KYC", "DOC-PAY-01"} <= doc_ids


def test_identity_pan_mismatch_flags_even_when_names_agree():
    finding = audit_identity_consistency(
        make_applicant("Rajesh Kumar Sharma", pan="ABCDE1234F"),
        "Rajesh Kumar Sharma",
        "Rajesh Kumar Sharma",
        tax_pan="ZZZZZ9999Z",
    )
    assert finding.verdict == "flag"
    assert "PAN" in finding.reason


def test_identity_pan_match_is_case_and_space_insensitive():
    finding = audit_identity_consistency(
        make_applicant("Rajesh Kumar Sharma", pan="ABCDE1234F"),
        "Rajesh Kumar Sharma",
        None,
        tax_pan=" abcde1234f ",
    )
    assert finding.verdict == "pass"


def test_identity_missing_kyc_returns_unknown():
    assert audit_identity_consistency(None, "Rajesh Kumar Sharma", "Rajesh Kumar Sharma").verdict == "unknown"


def test_identity_no_comparison_source_returns_unknown():
    # KYC present but nothing to check it against -> abstain, never a guessed pass.
    finding = audit_identity_consistency(make_applicant("Rajesh Kumar Sharma"), None, None)
    assert finding.verdict == "unknown"


def test_identity_ignores_the_spoofable_pass_shortcut():
    # Regression guard for the original stub, which returned 'pass' unconditionally
    # while ignoring both name arguments entirely.
    finding = audit_identity_consistency(make_applicant("Rajesh Kumar Sharma"), "Completely Different Name", "Another Person")
    assert finding.verdict != "pass"


# ── RULE-BANK-01: Bank Statement Arithmetic Validation ────────────────────────


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
    assert len(finding.supporting_evidence) == 4


def test_bank_arithmetic_mismatch_flags():
    ev_open = make_dummy_evidence("DOC-BANK", "10000.00")
    ev_cred = make_dummy_evidence("DOC-BANK", "5000.00")
    ev_deb = make_dummy_evidence("DOC-BANK", "2000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "12000.00")

    open_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_open)
    cred_fact = MoneyFact(amount=5000.00, currency="INR", basis="net", source=ev_cred)
    deb_fact = MoneyFact(amount=2000.00, currency="INR", basis="deduction", source=ev_deb)
    close_fact = MoneyFact(amount=12000.00, currency="INR", basis="balance", source=ev_close)

    finding = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=cred_fact,
        debits=deb_fact,
    )

    assert finding.verdict == "flag"
    assert "Bank statement arithmetic discrepancy" in finding.reason
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
    ]

    debits = [
        MoneyFact(amount=12000.00, currency="INR", source=make_dummy_evidence("DOC-BANK", "12000")),
        MoneyFact(amount=8000.00, currency="INR", source=make_dummy_evidence("DOC-BANK", "8000")),
    ]

    finding = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=credits,
        debits=debits,
    )

    assert finding.verdict == "pass"
    assert "Total Credits ₹37,500.00" in finding.reason
    assert "Total Debits ₹20,000.00" in finding.reason
    assert len(finding.supporting_evidence) == 7


def test_bank_arithmetic_zero_transactions_opening_equals_closing():
    ev_open = make_dummy_evidence("DOC-BANK", "15000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "15000.00")

    open_fact = MoneyFact(amount=15000.00, currency="INR", basis="balance", source=ev_open)
    close_fact = MoneyFact(amount=15000.00, currency="INR", basis="balance", source=ev_close)

    f_pass = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=[],
        debits=[],
    )
    assert f_pass.verdict == "pass"

    diff_close = MoneyFact(amount=14000.00, currency="INR", basis="balance", source=ev_close)
    f_flag = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=diff_close,
        credits=[],
        debits=[],
    )
    assert f_flag.verdict == "flag"


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


def test_bank_arithmetic_missing_transaction_amount_returns_unknown():
    ev_open = make_dummy_evidence("DOC-BANK", "10000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "15000.00")
    open_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_open)
    close_fact = MoneyFact(amount=15000.00, currency="INR", basis="balance", source=ev_close)

    bad_credit = {"amount": None, "source": make_dummy_evidence("DOC-BANK", "missing")}

    finding = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=[bad_credit],
        debits=[],
    )
    assert finding.verdict == "unknown"


def test_bank_arithmetic_invalid_transaction_amount_returns_unknown():
    ev_open = make_dummy_evidence("DOC-BANK", "10000.00")
    ev_close = make_dummy_evidence("DOC-BANK", "15000.00")
    open_fact = MoneyFact(amount=10000.00, currency="INR", basis="balance", source=ev_open)
    close_fact = MoneyFact(amount=15000.00, currency="INR", basis="balance", source=ev_close)

    bad_credit = {"amount": "not_a_number", "source": make_dummy_evidence("DOC-BANK", "bad")}
    f1 = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=[bad_credit],
        debits=[],
    )
    assert f1.verdict == "unknown"

    negative_debit = {"amount": -250.00, "source": make_dummy_evidence("DOC-BANK", "-250")}
    f2 = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_fact,
        credits=[],
        debits=[negative_debit],
    )
    assert f2.verdict == "unknown"


def test_bank_arithmetic_rounding_tolerance_boundary():
    ev = make_dummy_evidence("DOC-BANK", "test")
    open_fact = MoneyFact(amount=1000.00, currency="INR", basis="balance", source=ev)
    cred_fact = MoneyFact(amount=250.33, currency="INR", source=ev)
    deb_fact = MoneyFact(amount=100.28, currency="INR", source=ev)

    close_at_boundary = MoneyFact(amount=1150.10, currency="INR", basis="balance", source=ev)
    f_bound = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_at_boundary,
        credits=cred_fact,
        debits=deb_fact,
        tolerance=0.05,
    )
    assert f_bound.verdict == "pass"

    close_exceeding = MoneyFact(amount=1150.11, currency="INR", basis="balance", source=ev)
    f_exceed = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_exceeding,
        credits=cred_fact,
        debits=deb_fact,
        tolerance=0.05,
    )
    assert f_exceed.verdict == "flag"

    f_custom = validate_bank_statement_arithmetic(
        opening_balance=open_fact,
        closing_balance=close_exceeding,
        credits=cred_fact,
        debits=deb_fact,
        tolerance=0.10,
    )
    assert f_custom.verdict == "pass"
