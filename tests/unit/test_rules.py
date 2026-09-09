"""
Unit tests for deterministic financial and completeness rules.
Human-authored assertions ensuring money and completeness logic behaves deterministically.
"""

from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import ApplicantFact, MoneyFact
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
