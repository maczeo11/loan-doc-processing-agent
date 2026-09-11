"""
Unit tests for deterministic financial and completeness rules.
Human-authored assertions ensuring money and completeness logic behaves deterministically.
"""

from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import ApplicantFact, MoneyFact
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
