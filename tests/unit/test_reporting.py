"""
Unit tests for deterministic Credit Appraisal Memo (CAM) builder.
Human-authored tests ensuring formatting, PII masking, badges, and provenance.
"""
from typing import Dict, Any, List
from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import (
    ApplicantFact,
    PayslipFacts,
    BankStatementFacts,
    TaxReturnFacts,
    MoneyFact,
)
from core.contracts.findings import Finding
from core.contracts.state import LoanApplicationState
from core.reporting import (
    build_appraisal_memo,
    build_appraisal_summary,
    mask_pan,
    mask_account_number,
    mask_aadhaar,
)
from core.rules import evaluate_dossier_rules
from scripts.generate_dossiers import generate_dossier


def make_evidence(doc_id: str, doc_type: str, page: int, span: str) -> EvidenceRef:
    return EvidenceRef(
        document_id=doc_id,
        document_type=doc_type,
        page_number=page,
        quoted_span=span,
        bounding_box=BoundingBox(x0=50.0, y0=100.0, x1=500.0, y1=120.0),
        confidence=0.98,
    )


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


def test_pii_masking_pan():
    # Standard PAN
    assert mask_pan("ABCDE1234F") == "XXXXXX1234"
    # Pre-masked PAN
    assert mask_pan("XXXXXX1234") == "XXXXXX1234"
    # Edge cases
    assert mask_pan(None) == "UNKNOWN"
    assert mask_pan("UNKNOWN") == "UNKNOWN"
    assert mask_pan("") == "UNKNOWN"
    # Never exposes full alphanumeric PAN
    masked = mask_pan("ABCDE1234F")
    assert "ABCDE" not in masked
    assert masked.endswith("1234")


def test_pii_masking_account_number():
    # Long account number
    assert mask_account_number("501001234567") == "XXXXXXXX4567"
    # Already masked
    assert mask_account_number("XXXXXX9876") == "XXXXXXXX9876"
    # Edge cases
    assert mask_account_number(None) == "UNKNOWN"
    assert mask_account_number("UNKNOWN") == "UNKNOWN"
    assert mask_account_number("") == "UNKNOWN"
    # Never exposes full unmasked prefix
    masked = mask_account_number("501001234567")
    assert "501001" not in masked
    assert masked.endswith("4567")


def test_pii_masking_aadhaar():
    assert mask_aadhaar("123456789876") == "XXXX-XXXX-9876"
    assert mask_aadhaar("XXXX-XXXX-9876") == "XXXX-XXXX-9876"
    assert mask_aadhaar(None) == "UNKNOWN"


def test_memo_contains_all_six_required_sections():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    # 1. Executive Summary
    assert "## 1. Executive Summary" in memo
    # 2. Applicant Details
    assert "## 2. Applicant Details" in memo
    # 3. Financial Analysis
    assert "## 3. Financial Analysis" in memo
    # 4. Rule Findings
    assert "## 4. Rule Findings" in memo
    # 5. Evidence / Grounding
    assert "## 5. Evidence / Grounding" in memo
    # 6. Human Underwriter Review
    assert "## 6. Human Underwriter Review" in memo


def test_memo_badges_rendered_correctly():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    # PASS badge
    assert "✅ PASS" in memo
    # FLAG badge
    assert "⚠️ FLAG" in memo
    # UNKNOWN badge
    assert "❓ UNKNOWN" in memo

    # Verify each specific finding badge
    assert "✅ PASS RULE-COMP-01" in memo
    assert "✅ PASS RULE-INC-01" in memo
    assert "⚠️ FLAG RULE-TAX-01" in memo
    assert "❓ UNKNOWN RULE-ID-01" in memo


def test_finding_verdicts_preserved_without_alteration():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    # The reasons and verdicts must match the findings
    assert "All required documents are present." in memo
    assert "Salary verified within 5% tolerance." in memo
    assert "Tax discrepancy detected (12.0% mismatch)." in memo
    assert "Missing secondary ID record for cross-verification." in memo


def test_pii_is_masked_in_generated_memo():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    # Full PAN ABCDE1234F must NOT appear as the displayed PAN in applicant details
    assert "- **Permanent Account Number (PAN):** `XXXXXX1234`" in memo
    # Full account number 501001234567 must NOT appear
    assert "- **Account Number (Masked):** `XXXXXXXX4567`" in memo
    assert "501001234567" not in memo


def test_evidence_citations_included_in_findings():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    # Supporting evidence citations must be rendered with document ID, type, page, and span
    assert "[DOC-PAY-01]" in memo
    assert "payslip" in memo
    assert "Page 1" in memo
    assert 'Net Take Home: INR 85,000.00' in memo

    assert "[DOC-BANK-01]" in memo
    assert "bank_statement" in memo
    assert 'SALARY CREDIT: INR 85,000.00' in memo


def test_grounding_and_policy_citations_rendered():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    assert "CHUNK-POLICY-REQ-01" in memo
    assert "CHUNK-POLICY-SAL-02" in memo
    assert "- **Citation Grounding Gate Status:** ✅ PASS (Strictly Grounded)" in memo


def test_human_underwriter_review_section():
    state = create_full_test_state()
    memo = build_appraisal_memo(state)

    # Mandatory Underwriter Review section exists with signature and decision fields
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
    # Testing compatibility when state contains raw dicts instead of Pydantic models
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
            "account_number_masked": "123456789999",
            "closing_balance": {"amount": 50000.0, "currency": "INR"},
        },
        "findings": [
            {
                "rule_id": "RULE-INC-01",
                "rule_name": "Salary vs. Bank Credit",
                "verdict": "pass",
                "reason": "Salary matches exactly.",
                "supporting_evidence": [],
                "policy_version": "v1.0",
            }
        ],
        "document_ids": ["DOC-1"],
        "classified_types": {"DOC-1": "payslip"},
        "retrieved_chunk_ids": ["CHUNK-1"],
        "summary_grounded": True,
    }

    memo = build_appraisal_memo(dict_state)  # type: ignore
    assert "APP-DICT-99" in memo
    assert "Priya Patel" in memo
    assert "XXXXXX5678" in memo
    assert "XXXXXXXX9999" in memo
    assert "INR 80,000.00" in memo
    assert "✅ PASS RULE-INC-01" in memo


def test_clean_dossier_report(tmp_path):
    """Clean dossier: Report must show 5 passes, 0 flags, 0 unknown, with full provenance."""
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

    # 1. Verify all 6 mandatory sections are present
    assert "## 1. Executive Summary" in memo
    assert "## 2. Applicant Details" in memo
    assert "## 3. Financial Analysis" in memo
    assert "## 4. Rule Findings" in memo
    assert "## 5. Evidence / Grounding" in memo
    assert "## 6. Human Underwriter Review" in memo

    # 2. Executive summary counts
    assert "- **Total Rules Evaluated:** 5" in memo
    assert "- **Audit Verdict Summary:** 5 Passed | 0 Flagged | 0 Unknown" in memo
    assert "- **Missing Mandatory Documents:** None (All mandatory documents uploaded)" in memo

    # 3. Verdict grouping
    assert "#### ⚠️ Flagged Findings (Attention Required)" in memo
    assert "- None (No discrepancies flagged)." in memo
    assert "#### ✅ Passed Findings (Verified)" in memo
    assert "RULE-COMP-01" in memo
    assert "RULE-INC-01" in memo
    assert "RULE-TAX-01" in memo
    assert "RULE-ID-01" in memo
    assert "RULE-BANK-01" in memo

    # 4. Summary counts and lists
    assert summary["counts"] == {"total": 5, "pass": 5, "flag": 0, "unknown": 0}
    assert len(summary["pass_findings"]) == 5
    assert len(summary["flag_findings"]) == 0
    assert len(summary["unknown_findings"]) == 0


def test_flagged_dossier_report(tmp_path):
    """Flagged dossier: Flagged rules appear in attention section; reason and verdict preserved."""
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

    # Executive count verification
    assert "- **Audit Verdict Summary:** 4 Passed | 1 Flagged | 0 Unknown" in memo

    # Attention grouping
    assert "#### ⚠️ Flagged Findings (Attention Required)" in memo
    assert "RULE-INC-01" in memo
    assert "Salary discrepancy detected" in memo

    # Structured summary validation
    assert summary["counts"] == {"total": 5, "pass": 4, "flag": 1, "unknown": 0}
    assert len(summary["flag_findings"]) == 1
    assert summary["flag_findings"][0]["rule_id"] == "RULE-INC-01"
    assert summary["flag_findings"][0]["verdict"] == "flag"

    # Human sign-off notice remains present and no autonomous approval is granted
    assert "Autonomous credit lending decisions are strictly prohibited" in memo


def test_unknown_values_report(tmp_path):
    """Missing data dossier: Missing facts remain UNKNOWN, never zero or guessed."""
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

    # Missing financial facts strictly remain UNKNOWN
    assert "- **Gross Monthly Salary:** UNKNOWN" in memo
    assert "- **Net Take-Home Salary:** UNKNOWN" in memo
    assert "- **Average Monthly Salary Credit:** UNKNOWN" in memo
    assert "- **Gross Total Annual Income:** UNKNOWN" in memo

    # Unknown rule findings appear in unknown section
    assert "#### ❓ Unknown Findings (Information Needed / Incomplete)" in memo
    assert "RULE-INC-01" in memo
    assert "RULE-TAX-01" in memo

    # Missing documents listed
    assert "payslip_1.pdf" in memo

    # Summary structure
    assert summary["applicant_summary"]["full_name"] == "UNKNOWN"
    assert summary["financial_summary"]["payslip"]["gross_salary"] == "UNKNOWN"
    assert summary["counts"]["unknown"] == 2
    assert summary["counts"]["flag"] == 1  # RULE-COMP-01


def test_evidence_preservation_across_all_financial_facts():
    """All financial and applicant facts with EvidenceRefs preserve traceable citations."""
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
        employer_name="Wipro Ltd",
        gross_salary=MoneyFact(amount=150000.0, currency="INR", basis="gross", source=ev_gross),
        net_salary=MoneyFact(amount=120000.0, currency="INR", basis="net", source=ev_net),
        deductions_total=MoneyFact(amount=30000.0, currency="INR", basis="deduction", source=ev_ded),
    )
    bank = BankStatementFacts(
        account_holder="Kavita Rao",
        bank_name="Axis Bank",
        account_number_masked="987654321000",
        salary_credits=[MoneyFact(amount=120000.0, currency="INR", basis="net", source=ev_bank_sal)],
        average_salary_credit=MoneyFact(amount=120000.0, currency="INR", basis="net", source=ev_bank_sal),
        closing_balance=MoneyFact(amount=450000.0, currency="INR", basis="balance", source=ev_bank_close),
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

    # Verify identity citations
    assert "Identity Source Citation" in memo
    assert "[DOC-KYC-99]" in memo

    # Verify payslip citations
    assert "[DOC-PAY-01]" in memo
    assert "Gross Salary: INR 150,000.00" in memo
    assert "Net Salary: INR 120,000.00" in memo
    assert "PF Deduction: INR 30,000.00" in memo

    # Verify bank citations
    assert "[DOC-BANK-01]" in memo
    assert "SALARY CREDIT: INR 120,000.00" in memo
    assert "CLOSING BAL: INR 450,000.00" in memo

    # Verify tax citations
    assert "[DOC-TAX-01]" in memo
    assert "Gross Total Income: INR 1,800,000.00" in memo
    assert "Total Tax: INR 250,000.00" in memo

    # Verify structured summary has citation metadata
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
    """Findings are preserved exactly with rule_id, rule_name, verdict, reason, policy_version, evidence."""
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

    # In memo
    assert "RULE-CUSTOM-99" in memo
    assert "Custom Specialized Verification" in memo
    assert "⚠️ FLAG" in memo
    assert "Specific discrepancy of ₹12,345.67 detected." in memo
    assert "v2.1-custom" in memo
    assert "[DOC-TEST]" in memo
    assert "Test Span" in memo

    # In summary
    f_stored = summary["all_findings"][0]
    assert f_stored["rule_id"] == "RULE-CUSTOM-99"
    assert f_stored["rule_name"] == "Custom Specialized Verification"
    assert f_stored["verdict"] == "flag"
    assert f_stored["reason"] == "Specific discrepancy of ₹12,345.67 detected."
    assert f_stored["policy_version"] == "v2.1-custom"
    assert f_stored["supporting_evidence"][0]["document_id"] == "DOC-TEST"


def test_no_hallucinated_or_invented_values():
    """Empty or None values strictly produce UNKNOWN without hallucinating numbers or facts."""
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
    """Ensure PASS, FLAG, and UNKNOWN findings strictly retain their verdicts without coercion."""
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

    # Executive count verification
    assert "- **Audit Verdict Summary:** 1 Passed | 1 Flagged | 1 Unknown" in memo

    # Verdict groupings
    assert "#### ⚠️ Flagged Findings (Attention Required)" in memo
    assert "- **RULE-F (Flag Rule):** Clear flag." in memo
    assert "#### ✅ Passed Findings (Verified)" in memo
    assert "- **RULE-P (Pass Rule):** Clear pass." in memo
    assert "#### ❓ Unknown Findings (Information Needed / Incomplete)" in memo
    assert "- **RULE-U (Unknown Rule):** Clear unknown." in memo

    # Summary counts
    assert summary["counts"]["total"] == 3
    assert summary["counts"]["pass"] == 1
    assert summary["counts"]["flag"] == 1
    assert summary["counts"]["unknown"] == 1


def test_ground_truth_manifest_demarcation(tmp_path):
    """Manifest ground truth is clearly demarcated as benchmark only and non-extracted context."""
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

    # Check memo demarcation
    assert "### Dossier Manifest Reference (Synthetic Benchmark — Non-Extracted Context)" in memo
    assert "does NOT constitute extracted document evidence unless an explicit EvidenceRef is attached" in memo
    assert "- **Generation Scenario:** `clean`" in memo

    # Check summary demarcation
    gt = summary["manifest_ground_truth"]
    assert gt is not None
    assert gt["scenario"] == "clean"
    assert gt["is_extracted_evidence"] is False
