"""
Unit tests for deterministic Credit Appraisal Memo (CAM) assembly,
PII masking, and reviewed-dossier export.
"""

from typing import Any, Dict, List

import pytest

from core.contracts.evidence import BoundingBox, EvidenceRef
from core.contracts.facts import (
    ApplicantFact,
    BankStatementFacts,
    MoneyFact,
    PayslipFacts,
    TaxReturnFacts,
)
from core.contracts.findings import Finding
from core.contracts.state import LoanApplicationState
from core.reporting import (
    build_appraisal_memo,
    build_appraisal_summary,
    export_reviewed_dossier_json,
    export_reviewed_dossier_pdf,
    mask_aadhaar,
    mask_account_number,
    mask_pan,
)
from core.rules import evaluate_dossier_rules
from scripts.generate_dossiers import generate_dossier


def make_evidence(doc_id: str, doc_type: str = "payslip", page: int = 1, span: str = "test") -> EvidenceRef:
    return EvidenceRef(
        document_id=doc_id,
        document_type=doc_type,
        page_number=page,
        quoted_span=span,
        bounding_box=BoundingBox(x0=50.0, y0=100.0, x1=500.0, y1=120.0),
        confidence=0.98,
    )


def make_state(**overrides) -> dict:
    state = {
        "application_id": "APP-25195",
        "status": "READY_FOR_REVIEW",
        "applicant": ApplicantFact(full_name="Rajesh Kumar Sharma", source_name=make_evidence("DOC-KYC", "id_card", 1, "Rajesh")),
        "findings": [
            Finding(
                rule_id="RULE-INC-01",
                rule_name="Salary vs. Bank Credit Reconciliation",
                verdict="pass",
                reason="Salary verified within tolerance.",
            ),
            Finding(
                rule_id="RULE-TAX-01",
                rule_name="ITR Gross Income Reconciliation",
                verdict="flag",
                reason="Income discrepancy detected.",
            ),
        ],
        "retrieved_chunk_ids": ["credit_policy_v1_p2", "kyc_guidelines_v1_p1"],
        "missing_documents": [],
    }
    state.update(overrides)
    return state


def create_full_test_state() -> LoanApplicationState:
    ev_pan = make_evidence("DOC-KYC-01", "id_card", 1, "Permanent Account Number: ABCDE1234F")
    ev_payslip = make_evidence("DOC-PAY-01", "payslip", 1, "Net Take Home: INR 85,000.00")
    ev_bank = make_evidence("DOC-BANK-01", "bank_statement", 1, "SALARY CREDIT: INR 85,000.00")
    ev_tax = make_evidence("DOC-TAX-01", "tax_acknowledgement", 1, "Gross Total Income: INR 1,200,000.00")

    applicant = ApplicantFact(
        full_name="Aarav Sharma",
        source_name=ev_pan,
        dob="1992-05-15",
        pan_number="ABCDE1234F",
        source_pan=ev_pan,
        aadhaar_masked="XXXX-XXXX-9876",
    )

    payslip = PayslipFacts(
        employee_name="Aarav Sharma",
        employer_name="Tata Consultancy Services Ltd",
        gross_salary=MoneyFact(amount=100000.0, currency="INR", basis="gross", source=ev_payslip),
        net_salary=MoneyFact(amount=85000.0, currency="INR", basis="net", source=ev_payslip),
        deductions_total=MoneyFact(amount=15000.0, currency="INR", basis="deduction", source=ev_payslip),
        pay_period_str="August 2026",
    )

    bank = BankStatementFacts(
        account_holder="Aarav Sharma",
        bank_name="HDFC Bank Ltd",
        account_number_masked="501001234567",
        salary_credits=[MoneyFact(amount=85000.0, currency="INR", basis="net", source=ev_bank)],
        average_salary_credit=MoneyFact(amount=85000.0, currency="INR", basis="net", source=ev_bank),
        closing_balance=MoneyFact(amount=120000.0, currency="INR", basis="balance", source=ev_bank),
        bounced_transactions=0,
    )

    tax = TaxReturnFacts(
        assessee_name="Aarav Sharma",
        pan_number="ABCDE1234F",
        assessment_year="2025-26",
        gross_total_income=MoneyFact(amount=1200000.0, currency="INR", basis="gross", source=ev_tax),
        total_tax_paid=MoneyFact(amount=110000.0, currency="INR", basis="deduction", source=ev_tax),
    )

    findings: List[Finding] = [
        Finding(
            rule_id="RULE-COMP-01",
            rule_name="Dossier Completeness Check",
            verdict="pass",
            reason="All required documents are present.",
            supporting_evidence=[],
            policy_version="v1.0",
        ),
        Finding(
            rule_id="RULE-INC-01",
            rule_name="Salary vs. Bank Credit Reconciliation",
            verdict="pass",
            reason="Salary verified within 5% tolerance.",
            supporting_evidence=[ev_payslip, ev_bank],
            policy_version="v1.0",
        ),
        Finding(
            rule_id="RULE-TAX-01",
            rule_name="ITR Gross Income Reconciliation",
            verdict="flag",
            reason="Tax discrepancy detected (12.0% mismatch).",
            supporting_evidence=[ev_payslip, ev_tax],
            policy_version="v1.0",
        ),
        Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="Missing secondary ID record for cross-verification.",
            supporting_evidence=[ev_pan],
            policy_version="v1.0",
        ),
    ]

    return {
        "application_id": "APP-25195",
        "status": "READY_FOR_REVIEW",
        "status_history": [],
        "document_ids": ["DOC-KYC-01", "DOC-PAY-01", "DOC-BANK-01", "DOC-TAX-01"],
        "document_manifest": {},
        "document_bytes": None,
        "classified_types": {
            "DOC-KYC-01": "id_card",
            "DOC-PAY-01": "payslip",
            "DOC-BANK-01": "bank_statement",
            "DOC-TAX-01": "tax_acknowledgement",
        },
        "applicant": applicant,
        "payslip": payslip,
        "bank_statement": bank,
        "tax_return": tax,
        "findings": findings,
        "missing_documents": [],
        "retrieved_chunk_ids": ["CHUNK-POLICY-REQ-01", "CHUNK-POLICY-SAL-02"],
        "summary_markdown": None,
        "summary_grounded": True,
        "review_paused": True,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }


# ── Basic Memo Builder Tests ──────────────────────────────────────────────────


def test_memo_includes_application_and_applicant():
    memo = build_appraisal_memo(make_state())
    assert "APP-25195" in memo
    assert "Rajesh Kumar Sharma" in memo


def test_memo_renders_every_finding_with_its_verdict_badge():
    memo = build_appraisal_memo(make_state())
    assert "RULE-INC-01" in memo and "✅ PASS" in memo
    assert "RULE-TAX-01" in memo and "⚠️ FLAG" in memo


def test_memo_emits_bracketed_citations_for_the_grounding_gate():
    memo = build_appraisal_memo(make_state())
    assert "[credit_policy_v1_p2]" in memo
    assert "[kyc_guidelines_v1_p1]" in memo


def test_memo_reports_no_citations_when_retrieval_empty():
    memo = build_appraisal_memo(make_state(retrieved_chunk_ids=[]))
    assert "Referenced guidelines: None" in memo


def test_memo_lists_missing_documents():
    memo = build_appraisal_memo(make_state(missing_documents=["tax_acknowledgement", "id_card"]))
    assert "Missing Mandatory Documents" in memo
    assert "tax_acknowledgement" in memo


def test_memo_accepts_serialized_dict_findings():
    state = make_state(findings=[{"rule_id": "RULE-ID-01", "rule_name": "Identity", "verdict": "flag", "reason": "Name mismatch."}])
    memo = build_appraisal_memo(state)
    assert "RULE-ID-01" in memo
    assert "⚠️ FLAG" in memo


def test_memo_handles_absent_applicant():
    memo = build_appraisal_memo(make_state(applicant=None))
    assert "Unknown Applicant" in memo


# ── PII Masking Tests ─────────────────────────────────────────────────────────


def test_pii_masking_pan():
    assert mask_pan("ABCDE1234F") == "XXXXXX1234"
    assert mask_pan("XXXXXX1234") == "XXXXXX1234"
    assert mask_pan(None) == "UNKNOWN"
    assert mask_pan("UNKNOWN") == "UNKNOWN"
    assert mask_pan("") == "UNKNOWN"
    masked = mask_pan("ABCDE1234F")
    assert "ABCDE" not in masked
    assert masked.endswith("1234")


def test_pii_masking_account_number():
    assert mask_account_number("501001234567") == "XXXXXXXX4567"
    assert mask_account_number("XXXXXX9876") == "XXXXXXXX9876"
    assert mask_account_number(None) == "UNKNOWN"
    assert mask_account_number("UNKNOWN") == "UNKNOWN"
    assert mask_account_number("") == "UNKNOWN"
    masked = mask_account_number("501001234567")
    assert "501001" not in masked
    assert masked.endswith("4567")


def test_pii_masking_aadhaar():
    assert mask_aadhaar("123456789876") == "XXXX-XXXX-9876"
    assert mask_aadhaar("XXXX-XXXX-9876") == "XXXX-XXXX-9876"
    assert mask_aadhaar(None) == "UNKNOWN"


# ── 6-Section & Structure Tests ───────────────────────────────────────────────


def test_memo_contains_all_six_required_sections():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    assert "## 1. Executive Summary" in memo
    assert "## 2. Applicant Details" in memo
    assert "## 3. Financial Analysis" in memo
    assert "## 4. Rule Findings" in memo
    assert "## 5. Evidence / Grounding" in memo
    assert "## 6. Human Underwriter Review" in memo


def test_memo_badges_rendered_correctly():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    assert "✅ PASS" in memo
    assert "⚠️ FLAG" in memo
    assert "❓ UNKNOWN" in memo

    assert "✅ PASS RULE-COMP-01" in memo
    assert "✅ PASS RULE-INC-01" in memo
    assert "⚠️ FLAG RULE-TAX-01" in memo
    assert "❓ UNKNOWN RULE-ID-01" in memo


def test_finding_verdicts_preserved_without_alteration():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    assert "All required documents are present." in memo
    assert "Salary verified within 5% tolerance." in memo
    assert "Tax discrepancy detected (12.0% mismatch)." in memo
    assert "Missing secondary ID record for cross-verification." in memo


def test_pii_is_masked_in_generated_memo():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    assert "- **Permanent Account Number (PAN):** `XXXXXX1234`" in memo
    assert "- **Account Number (Masked):** `XXXXXXXX4567`" in memo
    assert "501001234567" not in memo


def test_evidence_citations_included_in_findings():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    assert "[DOC-PAY-01]" in memo
    assert "payslip" in memo
    assert "Page 1" in memo
    assert "Net Take Home: INR 85,000.00" in memo

    assert "[DOC-BANK-01]" in memo
    assert "bank_statement" in memo
    assert "SALARY CREDIT: INR 85,000.00" in memo


def test_grounding_and_policy_citations_rendered():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    assert "CHUNK-POLICY-REQ-01" in memo
    assert "CHUNK-POLICY-SAL-02" in memo
    assert "- **Citation Grounding Gate Status:** ✅ PASS (Strictly Grounded)" in memo


def test_human_underwriter_review_section():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    assert "## 6. Human Underwriter Review" in memo
    assert "MANDATORY UNDERWRITER SIGN-OFF NOTICE" in memo
    assert "- **Reviewer:** _________________________________________" in memo
    assert "- **Decision:** [ ] APPROVED   [ ] REJECTED   [ ] NEEDS_INFO" in memo
    assert "- **Comments:** _________________________________________" in memo
    assert "- **Signature:** _________________________________________" in memo
    assert "- **Date:** ____________________" in memo


def test_empty_or_missing_state_displays_unknown_and_does_not_crash():
    empty_state: LoanApplicationState = {
        "application_id": "APP-EMPTY",
        "status": "READY_FOR_REVIEW",
        "status_history": [],
        "document_ids": [],
        "document_manifest": {},
        "document_bytes": None,
        "classified_types": {},
        "applicant": None,
        "payslip": None,
        "bank_statement": None,
        "tax_return": None,
        "findings": [],
        "missing_documents": ["application_form", "payslip", "bank_statement"],
        "retrieved_chunk_ids": [],
        "summary_markdown": None,
        "summary_grounded": False,
        "review_paused": True,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }

    memo = build_appraisal_memo(empty_state)

    assert "APP-EMPTY" in memo
    assert "- **Applicant Full Name:** UNKNOWN" in memo
    assert "- **Permanent Account Number (PAN):** `UNKNOWN`" in memo
    assert "- **Gross Monthly Salary:** UNKNOWN" in memo
    assert "- **Average Monthly Salary Credit:** UNKNOWN" in memo
    assert "- **Gross Total Annual Income:** UNKNOWN" in memo
    assert "- **Missing Mandatory Documents:** ⚠️ `application_form, payslip, bank_statement`" in memo
    assert "No deterministic rule findings have been evaluated." in memo
    assert "## 6. Human Underwriter Review" in memo


def test_handles_dict_based_facts_and_findings():
    dict_state: Dict[str, Any] = {
        "application_id": "APP-DICT-99",
        "status": "PROCESSING",
        "applicant": {
            "full_name": "Priya Patel",
            "pan_number": "ABCDE5678F",
            "aadhaar_masked": "XXXX-XXXX-1111",
        },
        "payslip": {
            "employer_name": "Infosys Technologies Ltd",
            "gross_salary": {"amount": 80000.0, "currency": "INR"},
            "net_salary": {"amount": 70000.0, "currency": "INR"},
        },
        "bank_statement": {
            "bank_name": "State Bank of India",
            "account_holder": "Priya Patel",
            "account_number_masked": "123456789012",
            "closing_balance": {"amount": 50000.0, "currency": "INR"},
        },
        "tax_return": {
            "assessee_name": "Priya Patel",
            "pan_number": "ABCDE5678F",
            "gross_total_income": {"amount": 960000.0, "currency": "INR"},
        },
        "findings": [
            {
                "rule_id": "RULE-COMP-01",
                "rule_name": "Dossier Completeness Check",
                "verdict": "pass",
                "reason": "Complete.",
            }
        ],
    }

    memo = build_appraisal_memo(dict_state)
    summary = build_appraisal_summary(dict_state)

    assert "Priya Patel" in memo
    assert "XXXXXX5678" in memo
    assert "Infosys Technologies Ltd" in memo
    assert "INR 80,000.00" in memo
    assert "RULE-COMP-01" in memo
    assert summary["counts"]["pass"] == 1


def test_clean_dossier_report(tmp_path):
    manifest = generate_dossier(seed=301, scenario="clean", output_dir=str(tmp_path))
    findings = evaluate_dossier_rules(dossier_manifest=manifest)

    state: Dict[str, Any] = {
        "application_id": manifest["application_id"],
        "status": "READY_FOR_REVIEW",
        "document_ids": manifest["expected_documents"],
        "classified_types": {d: d.split("_")[0] for d in manifest["expected_documents"]},
        "findings": findings,
        "missing_documents": [],
        "retrieved_chunk_ids": ["CHUNK-POLICY-01"],
        "summary_grounded": True,
    }

    memo = build_appraisal_memo(state, manifest=manifest)
    summary = build_appraisal_summary(state, manifest=manifest)

    assert "## 1. Executive Summary" in memo
    assert "## 2. Applicant Details" in memo
    assert "## 3. Financial Analysis" in memo
    assert "## 4. Rule Findings" in memo
    assert "## 5. Evidence / Grounding" in memo
    assert "## 6. Human Underwriter Review" in memo
    assert summary["counts"]["pass"] == 5
    assert summary["counts"]["flag"] == 0


def test_flagged_dossier_report(tmp_path):
    manifest = generate_dossier(seed=302, scenario="salary_mismatch", output_dir=str(tmp_path))
    findings = evaluate_dossier_rules(dossier_manifest=manifest)

    state: Dict[str, Any] = {
        "application_id": manifest["application_id"],
        "status": "READY_FOR_REVIEW",
        "document_ids": manifest["expected_documents"],
        "classified_types": {d: d.split("_")[0] for d in manifest["expected_documents"]},
        "findings": findings,
        "missing_documents": [],
        "retrieved_chunk_ids": ["CHUNK-POLICY-SAL"],
        "summary_grounded": True,
    }

    memo = build_appraisal_memo(state, manifest=manifest)
    summary = build_appraisal_summary(state, manifest=manifest)

    assert "- **Audit Verdict Summary:** 4 Passed | 1 Flagged | 0 Unknown" in memo
    assert "#### ⚠️ Flagged Findings (Attention Required)" in memo
    assert "RULE-INC-01" in memo
    assert "Salary discrepancy detected" in memo


def test_unknown_values_report(tmp_path):
    manifest = generate_dossier(seed=303, scenario="missing_payslip", output_dir=str(tmp_path))
    findings = evaluate_dossier_rules(dossier_manifest=manifest)

    state: Dict[str, Any] = {
        "application_id": manifest["application_id"],
        "status": "NEEDS_INFORMATION",
        "document_ids": manifest["generated_document_names"],
        "classified_types": {d: d.split("_")[0] for d in manifest["generated_document_names"]},
        "applicant": None,
        "payslip": None,
        "bank_statement": None,
        "tax_return": None,
        "findings": findings,
        "missing_documents": ["payslip_1.pdf", "payslip_2.pdf", "payslip_3.pdf"],
    }

    memo = build_appraisal_memo(state)
    summary = build_appraisal_summary(state)

    assert "- **Gross Monthly Salary:** UNKNOWN" in memo
    assert "- **Net Take-Home Salary:** UNKNOWN" in memo
    assert "- **Average Monthly Salary Credit:** UNKNOWN" in memo
    assert "- **Gross Total Annual Income:** UNKNOWN" in memo


def test_evidence_preservation_across_all_financial_facts():
    ev_pan = make_evidence("DOC-KYC-99", "id_card", 1, "PAN: FGHIJ5678K")
    ev_gross = make_evidence("DOC-PAY-01", "payslip", 1, "Gross Salary: INR 150,000.00")
    ev_net = make_evidence("DOC-PAY-01", "payslip", 1, "Net Salary: INR 120,000.00")
    ev_ded = make_evidence("DOC-PAY-01", "payslip", 1, "PF Deduction: INR 30,000.00")
    ev_bank_sal = make_evidence("DOC-BANK-01", "bank_statement", 2, "SALARY CREDIT: INR 120,000.00")
    ev_bank_close = make_evidence("DOC-BANK-01", "bank_statement", 3, "CLOSING BAL: INR 450,000.00")
    ev_tax_gross = make_evidence("DOC-TAX-01", "tax_acknowledgement", 1, "Gross Total Income: INR 1,800,000.00")
    ev_tax_paid = make_evidence("DOC-TAX-01", "tax_acknowledgement", 1, "Total Tax: INR 250,000.00")

    applicant = ApplicantFact(
        full_name="Kavita Rao",
        source_name=ev_pan,
        pan_number="FGHIJ5678K",
        source_pan=ev_pan,
    )
    payslip = PayslipFacts(
        employee_name="Kavita Rao",
        employer_name="Acme Corp",
        gross_salary=MoneyFact(amount=150000.0, currency="INR", basis="gross", source=ev_gross),
        net_salary=MoneyFact(amount=120000.0, currency="INR", basis="net", source=ev_net),
        deductions_total=MoneyFact(amount=30000.0, currency="INR", basis="deduction", source=ev_ded),
    )
    bank = BankStatementFacts(
        account_holder="Kavita Rao",
        bank_name="State Bank of India",
        account_number_masked="1234567890",
        closing_balance=MoneyFact(amount=450000.0, currency="INR", basis="balance", source=ev_bank_close),
        average_salary_credit=MoneyFact(amount=120000.0, currency="INR", basis="net", source=ev_bank_sal),
    )
    tax = TaxReturnFacts(
        assessee_name="Kavita Rao",
        pan_number="FGHIJ5678K",
        assessment_year="2025-26",
        gross_total_income=MoneyFact(amount=1800000.0, currency="INR", basis="gross", source=ev_tax_gross),
        total_tax_paid=MoneyFact(amount=250000.0, currency="INR", basis="deduction", source=ev_tax_paid),
    )

    state: LoanApplicationState = {
        "application_id": "APP-EVIDENCE-TEST",
        "status": "READY_FOR_REVIEW",
        "status_history": [],
        "document_ids": ["DOC-KYC-99", "DOC-PAY-01", "DOC-BANK-01", "DOC-TAX-01"],
        "document_manifest": {},
        "document_bytes": None,
        "classified_types": {},
        "applicant": applicant,
        "payslip": payslip,
        "bank_statement": bank,
        "tax_return": tax,
        "findings": [],
        "missing_documents": [],
        "retrieved_chunk_ids": [],
        "summary_markdown": None,
        "summary_grounded": True,
        "review_paused": True,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }

    memo = build_appraisal_memo(state)
    summary = build_appraisal_summary(state)

    assert "Identity Source Citation" in memo
    assert "[DOC-KYC-99]" in memo

    assert "[DOC-PAY-01]" in memo
    assert "Gross Salary: INR 150,000.00" in memo
    assert "Net Salary: INR 120,000.00" in memo
    assert "PF Deduction: INR 30,000.00" in memo

    assert "[DOC-BANK-01]" in memo
    assert "SALARY CREDIT: INR 120,000.00" in memo
    assert "CLOSING BAL: INR 450,000.00" in memo

    assert "[DOC-TAX-01]" in memo
    assert "Gross Total Income: INR 1,800,000.00" in memo
    assert "Total Tax: INR 250,000.00" in memo

    ps_sum = summary["financial_summary"]["payslip"]
    assert "DOC-PAY-01" in ps_sum["gross_salary_citation"]
    assert "DOC-PAY-01" in ps_sum["net_salary_citation"]
    assert "DOC-PAY-01" in ps_sum["deductions_citation"]

    bs_sum = summary["financial_summary"]["bank_statement"]
    assert "DOC-BANK-01" in bs_sum["closing_balance_citation"]
    assert "DOC-BANK-01" in bs_sum["average_salary_credit_citation"]

    tr_sum = summary["financial_summary"]["tax_return"]
    assert "DOC-TAX-01" in tr_sum["gross_total_income_citation"]
    assert "DOC-TAX-01" in tr_sum["total_tax_paid_citation"]


def test_findings_preservation_exact():
    ev = make_evidence("DOC-TEST", "payslip", 2, "Test Span")
    finding = Finding(
        rule_id="RULE-CUSTOM-99",
        rule_name="Custom Specialized Verification",
        verdict="flag",
        reason="Specific discrepancy of ₹12,345.67 detected.",
        supporting_evidence=[ev],
        policy_version="v2.1-custom",
    )

    state: Dict[str, Any] = {
        "application_id": "APP-FINDING-EXACT",
        "findings": [finding],
    }

    memo = build_appraisal_memo(state)
    summary = build_appraisal_summary(state)

    assert "RULE-CUSTOM-99" in memo
    assert "Custom Specialized Verification" in memo
    assert "⚠️ FLAG" in memo
    assert "Specific discrepancy of ₹12,345.67 detected." in memo
    assert "v2.1-custom" in memo
    assert "[DOC-TEST]" in memo
    assert "Test Span" in memo

    f_stored = summary["all_findings"][0]
    assert f_stored["rule_id"] == "RULE-CUSTOM-99"
    assert f_stored["rule_name"] == "Custom Specialized Verification"
    assert f_stored["verdict"] == "flag"
    assert f_stored["reason"] == "Specific discrepancy of ₹12,345.67 detected."
    assert f_stored["policy_version"] == "v2.1-custom"
    assert f_stored["supporting_evidence"][0]["document_id"] == "DOC-TEST"


def test_no_hallucinated_or_invented_values():
    minimal_state: Dict[str, Any] = {
        "application_id": "APP-MINIMAL",
    }

    memo = build_appraisal_memo(minimal_state)
    summary = build_appraisal_summary(minimal_state)

    assert "- **Applicant Full Name:** UNKNOWN" in memo
    assert "- **Date of Birth:** UNKNOWN" in memo
    assert "- **Permanent Account Number (PAN):** `UNKNOWN`" in memo
    assert "- **Aadhaar ID (Masked):** `UNKNOWN`" in memo
    assert "- **Employer / Organization:** UNKNOWN" in memo
    assert "- **Gross Monthly Salary:** UNKNOWN" in memo
    assert "- **Net Take-Home Salary:** UNKNOWN" in memo
    assert "- **Total Deductions:** UNKNOWN" in memo
    assert "- **Average Monthly Salary Credit:** UNKNOWN" in memo
    assert "- **Closing Account Balance:** UNKNOWN" in memo
    assert "- **Gross Total Annual Income:** UNKNOWN" in memo
    assert "- **Total Tax Paid:** UNKNOWN" in memo

    assert summary["applicant_summary"]["full_name"] == "UNKNOWN"
    assert summary["financial_summary"]["payslip"]["gross_salary"] == "UNKNOWN"


def test_pass_flag_unknown_values_remain_unchanged():
    findings = [
        Finding(
            rule_id="RULE-P",
            rule_name="Pass Rule",
            verdict="pass",
            reason="Clear pass.",
            supporting_evidence=[],
            policy_version="v1.0",
        ),
        Finding(
            rule_id="RULE-F",
            rule_name="Flag Rule",
            verdict="flag",
            reason="Clear flag.",
            supporting_evidence=[],
            policy_version="v1.0",
        ),
        Finding(
            rule_id="RULE-U",
            rule_name="Unknown Rule",
            verdict="unknown",
            reason="Clear unknown.",
            supporting_evidence=[],
            policy_version="v1.0",
        ),
    ]

    state: Dict[str, Any] = {
        "application_id": "APP-VERDICTS",
        "findings": findings,
    }

    memo = build_appraisal_memo(state)
    summary = build_appraisal_summary(state)

    assert "- **Audit Verdict Summary:** 1 Passed | 1 Flagged | 1 Unknown" in memo
    assert "#### ⚠️ Flagged Findings (Attention Required)" in memo
    assert "- **RULE-F (Flag Rule):** Clear flag." in memo
    assert "#### ✅ Passed Findings (Verified)" in memo
    assert "- **RULE-P (Pass Rule):** Clear pass." in memo
    assert "#### ❓ Unknown Findings (Information Needed / Incomplete)" in memo
    assert "- **RULE-U (Unknown Rule):** Clear unknown." in memo

    assert summary["counts"]["total"] == 3
    assert summary["counts"]["pass"] == 1
    assert summary["counts"]["flag"] == 1
    assert summary["counts"]["unknown"] == 1


def test_ground_truth_manifest_demarcation(tmp_path):
    manifest = generate_dossier(seed=304, scenario="clean", output_dir=str(tmp_path))

    state: Dict[str, Any] = {
        "application_id": manifest["application_id"],
        "status": "READY_FOR_REVIEW",
        "document_ids": manifest["expected_documents"],
        "classified_types": {},
        "findings": [],
    }

    memo = build_appraisal_memo(state, manifest=manifest)
    summary = build_appraisal_summary(state, manifest=manifest)

    assert "### Dossier Manifest Reference (Synthetic Benchmark — Non-Extracted Context)" in memo
    assert "does NOT constitute extracted document evidence unless an explicit EvidenceRef is attached" in memo
    assert "- **Generation Scenario:** `clean`" in memo

    gt = summary["manifest_ground_truth"]
    assert gt is not None
    assert gt["scenario"] == "clean"
    assert gt["is_extracted_evidence"] is False


# ── Exporter Tests ────────────────────────────────────────────────────────────


def test_json_export_returns_full_state():
    exported = export_reviewed_dossier_json(make_state())
    assert exported["application_id"] == "APP-25195"
    assert len(exported["findings"]) == 2


def test_pdf_export_writes_a_real_pdf(tmp_path):
    pytest.importorskip("reportlab")
    out = tmp_path / "APP-25195.pdf"
    state = make_state(summary_markdown=build_appraisal_memo(make_state()))

    returned = export_reviewed_dossier_pdf(state, str(out))

    assert returned == str(out)
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF-")


def test_pdf_export_creates_missing_parent_directory(tmp_path):
    pytest.importorskip("reportlab")
    out = tmp_path / "nested" / "dir" / "APP-25195.pdf"
    export_reviewed_dossier_pdf(make_state(), str(out))
    assert out.exists()


def test_pdf_export_paginates_long_memos_without_crashing(tmp_path):
    pytest.importorskip("reportlab")
    out = tmp_path / "long.pdf"
    long_memo = "\n".join(f"Policy clause line {i} " + ("x" * 200) for i in range(300))
    export_reviewed_dossier_pdf(make_state(summary_markdown=long_memo), str(out))
    assert out.exists()
    assert out.stat().st_size > 0
