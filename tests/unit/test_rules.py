"""
Unit tests for deterministic financial and completeness rules.
Human-authored assertions ensuring money and completeness logic behaves deterministically.
"""

from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import MoneyFact
from core.rules.completeness import evaluate_completeness
from core.rules.salary_audit import audit_salary_vs_bank


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
