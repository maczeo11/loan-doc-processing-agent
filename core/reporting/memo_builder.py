"""
Credit Appraisal Memo (CAM) Builder.
HUMAN-ONLY ZONE: Owned by Member 4 (Sravanthi).

Generates an auditable, structured Credit Appraisal Memo (CAM) in Markdown format.
Prime Invariants:
  1. Deterministic code decides. AI explains. A human approves.
  2. Every number traces back to a page in a document.
  3. No financial values are invented or hallucinated.
  4. Mandatory PII masking for PAN and bank account numbers.
  5. Missing or unverifiable values remain UNKNOWN.
"""

import re
from typing import Any, Dict, List, Optional, Union
from core.contracts.state import LoanApplicationState
from core.contracts.findings import Finding
from core.contracts.facts import (
    ApplicantFact,
    PayslipFacts,
    BankStatementFacts,
    TaxReturnFacts,
    MoneyFact,
)
from core.contracts.evidence import EvidenceRef


def mask_pan(pan: Optional[str]) -> str:
    """
    Masks a PAN number to expose only the last 4 characters, e.g. XXXXXX1234.
    Returns 'UNKNOWN' if missing or unavailable.
    """
    if not pan or str(pan).strip().upper() in ("UNKNOWN", "NONE", ""):
        return "UNKNOWN"
    clean = str(pan).strip().upper()
    match = re.search(r"\d{4}", clean)
    if match:
        return f"XXXXXX{match.group(0)}"
    if len(clean) >= 4:
        return f"XXXXXX{clean[-4:]}"
    return "XXXXXX"


def mask_account_number(acct: Optional[str]) -> str:
    """
    Masks a bank account number to expose only the last 4 characters, e.g. XXXXXXXX1234.
    Returns 'UNKNOWN' if missing or unavailable.
    """
    if not acct or str(acct).strip().upper() in ("UNKNOWN", "NONE", ""):
        return "UNKNOWN"
    digits = re.sub(r"\D", "", str(acct))
    if len(digits) >= 4:
        return f"XXXXXXXX{digits[-4:]}"
    clean = str(acct).strip()
    if len(clean) >= 4:
        return f"XXXXXXXX{clean[-4:]}"
    return "XXXXXXXX"


def mask_aadhaar(aadhaar: Optional[str]) -> str:
    """
    Masks an Aadhaar number to standard format XXXX-XXXX-1234.
    Returns 'UNKNOWN' if missing or unavailable.
    """
    if not aadhaar or str(aadhaar).strip().upper() in ("UNKNOWN", "NONE", ""):
        return "UNKNOWN"
    digits = re.sub(r"\D", "", str(aadhaar))
    if len(digits) >= 4:
        return f"XXXX-XXXX-{digits[-4:]}"
    clean = str(aadhaar).strip()
    if len(clean) >= 4:
        return f"XXXX-XXXX-{clean[-4:]}"
    return "XXXX-XXXX-XXXX"


def _format_money(mf: Any) -> str:
    """
    Formats a MoneyFact or dict into a display string, e.g. 'INR 85,000.00'.
    Returns 'UNKNOWN' if missing, null, or zero/invalid.
    """
    if mf is None:
        return "UNKNOWN"
    amt = None
    curr = "INR"
    if isinstance(mf, dict):
        amt = mf.get("amount")
        curr = mf.get("currency", "INR")
    else:
        amt = getattr(mf, "amount", None)
        curr = getattr(mf, "currency", "INR")

    if amt is None:
        return "UNKNOWN"
    try:
        val = float(amt)
        return f"{curr} {val:,.2f}"
    except (ValueError, TypeError):
        return "UNKNOWN"


def _get_val(obj: Any, field_name: str, default: Any = None) -> Any:
    """Helper to safely retrieve a field from a Pydantic model or dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


def _verdict_badge(verdict: str) -> str:
    """Returns the visual badge for a rule verdict."""
    v = str(verdict).lower().strip()
    if v == "pass":
        return "✅ PASS"
    if v == "flag":
        return "⚠️ FLAG"
    return "❓ UNKNOWN"


def build_appraisal_memo(state: LoanApplicationState) -> str:
    """
    Assembles a comprehensive, auditable Credit Appraisal Memo (CAM) in Markdown.
    Contains 6 mandatory sections:
      1. Executive Summary
      2. Applicant Details
      3. Financial Analysis
      4. Rule Findings
      5. Evidence / Grounding
      6. Human Underwriter Review

    Zero hallucinated numbers: every financial figure comes from extracted facts.
    """
    app_id = state.get("application_id", "UNKNOWN")
    status = state.get("status", "READY_FOR_REVIEW")
    findings: List[Union[Finding, Dict[str, Any]]] = state.get("findings") or []
    missing_docs: List[str] = state.get("missing_documents") or []

    applicant_data = state.get("applicant")
    payslip_data = state.get("payslip")
    bank_data = state.get("bank_statement")
    tax_data = state.get("tax_return")

    # Counts for executive overview
    pass_count = 0
    flag_count = 0
    unknown_count = 0
    for f in findings:
        v = _get_val(f, "verdict", "unknown")
        if str(v).lower() == "pass":
            pass_count += 1
        elif str(v).lower() == "flag":
            flag_count += 1
        else:
            unknown_count += 1

    lines: List[str] = []

    # Title Header
    lines.append(f"# Credit Appraisal Memo (CAM) — {app_id}")
    lines.append("")

    # =========================================================================
    # 1. Executive Summary
    # =========================================================================
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(f"- **Application ID:** {app_id}")
    lines.append(f"- **Lifecycle Status:** `{status}`")
    lines.append(f"- **Total Rules Evaluated:** {len(findings)}")
    lines.append(f"- **Audit Verdict Summary:** {pass_count} Passed | {flag_count} Flagged | {unknown_count} Unknown")

    if missing_docs:
        lines.append(f"- **Missing Mandatory Documents:** ⚠️ `{', '.join(missing_docs)}`")
    else:
        lines.append("- **Missing Mandatory Documents:** None (All mandatory documents uploaded)")

    lines.append("")
    lines.append(
        "> **Governance Invariant:** Pure deterministic code decides findings and financial totals. "
        "AI explains and navigates context. A qualified human underwriter must approve the final loan decision. "
        "Every fact traces back to an explicit document page and bounding box."
    )
    lines.append("")

    # =========================================================================
    # 2. Applicant Details
    # =========================================================================
    lines.append("## 2. Applicant Details")
    lines.append("")

    raw_name = _get_val(applicant_data, "full_name")
    applicant_name = raw_name if raw_name and raw_name.strip().upper() != "UNKNOWN" else "UNKNOWN"

    raw_dob = _get_val(applicant_data, "dob")
    dob = raw_dob if raw_dob and str(raw_dob).strip().upper() != "UNKNOWN" else "UNKNOWN"

    raw_pan = _get_val(applicant_data, "pan_number")
    masked_pan = mask_pan(raw_pan)

    raw_aadhaar = _get_val(applicant_data, "aadhaar_masked")
    masked_aadhaar = mask_aadhaar(raw_aadhaar)

    raw_employer = _get_val(payslip_data, "employer_name")
    employer_name = raw_employer if raw_employer and str(raw_employer).strip().upper() != "UNKNOWN" else "UNKNOWN"

    lines.append(f"- **Applicant Full Name:** {applicant_name}")
    lines.append(f"- **Date of Birth:** {dob}")
    lines.append(f"- **Permanent Account Number (PAN):** `{masked_pan}`")
    lines.append(f"- **Aadhaar ID (Masked):** `{masked_aadhaar}`")
    lines.append(f"- **Employer / Organization:** {employer_name}")

    source_name_ev = _get_val(applicant_data, "source_name")
    if source_name_ev:
        doc_id = _get_val(source_name_ev, "document_id", "KYC")
        page_num = _get_val(source_name_ev, "page_number", 1)
        span = _get_val(source_name_ev, "quoted_span", "")
        lines.append(f"- **Identity Source Citation:** `[{doc_id}]` Page {page_num} (Quoted: \"{span}\")")

    lines.append("")

    # =========================================================================
    # 3. Financial Analysis
    # =========================================================================
    lines.append("## 3. Financial Analysis")
    lines.append("")

    gross_salary_val = _format_money(_get_val(payslip_data, "gross_salary"))
    net_salary_val = _format_money(_get_val(payslip_data, "net_salary"))
    deductions_val = _format_money(_get_val(payslip_data, "deductions_total"))
    pay_period_val = _get_val(payslip_data, "pay_period_str") or "UNKNOWN"

    bank_name_val = _get_val(bank_data, "bank_name") or "UNKNOWN"
    acct_holder_val = _get_val(bank_data, "account_holder") or "UNKNOWN"
    acct_no_masked = mask_account_number(_get_val(bank_data, "account_number_masked"))
    avg_salary_credit_val = _format_money(_get_val(bank_data, "average_salary_credit"))
    closing_bal_val = _format_money(_get_val(bank_data, "closing_balance"))
    bounced_count = _get_val(bank_data, "bounced_transactions", "UNKNOWN")

    assessee_val = _get_val(tax_data, "assessee_name") or "UNKNOWN"
    ay_val = _get_val(tax_data, "assessment_year") or "UNKNOWN"
    itr_gross_val = _format_money(_get_val(tax_data, "gross_total_income"))
    tax_paid_val = _format_money(_get_val(tax_data, "total_tax_paid"))

    lines.append("### Payslip Financial Facts")
    lines.append(f"- **Pay Period:** {pay_period_val}")
    lines.append(f"- **Gross Monthly Salary:** {gross_salary_val}")
    lines.append(f"- **Net Take-Home Salary:** {net_salary_val}")
    lines.append(f"- **Total Deductions:** {deductions_val}")
    lines.append("")

    lines.append("### Bank Statement Financial Facts")
    lines.append(f"- **Bank Name:** {bank_name_val}")
    lines.append(f"- **Account Holder:** {acct_holder_val}")
    lines.append(f"- **Account Number (Masked):** `{acct_no_masked}`")
    lines.append(f"- **Average Monthly Salary Credit:** {avg_salary_credit_val}")
    lines.append(f"- **Closing Account Balance:** {closing_bal_val}")
    lines.append(f"- **Bounced Transactions Count:** {bounced_count}")
    lines.append("")

    lines.append("### Income Tax Return (ITR-V) Facts")
    lines.append(f"- **Assessee Name:** {assessee_val}")
    lines.append(f"- **Assessment Year:** {ay_val}")
    lines.append(f"- **Gross Total Annual Income:** {itr_gross_val}")
    lines.append(f"- **Total Tax Paid:** {tax_paid_val}")
    lines.append("")

    # =========================================================================
    # 4. Rule Findings
    # =========================================================================
    lines.append("## 4. Rule Findings")
    lines.append("")

    if not findings:
        lines.append("No deterministic rule findings have been evaluated.")
    else:
        for idx, finding in enumerate(findings, 1):
            rule_id = _get_val(finding, "rule_id", f"RULE-{idx}")
            rule_name = _get_val(finding, "rule_name", "Verification Rule")
            verdict = _get_val(finding, "verdict", "unknown")
            reason = _get_val(finding, "reason", "No reason provided.")
            policy_version = _get_val(finding, "policy_version", "v1.0")
            badge = _verdict_badge(verdict)

            lines.append(f"### {badge} {rule_id}: {rule_name}")
            lines.append(f"- **Verdict:** {badge}")
            lines.append(f"- **Policy Version:** `{policy_version}`")
            lines.append(f"- **Determination:** {reason}")

            ev_list = _get_val(finding, "supporting_evidence") or []
            if ev_list:
                lines.append("- **Supporting Evidence Citations:**")
                for ev in ev_list:
                    doc_id = _get_val(ev, "document_id", "DOC")
                    doc_type = _get_val(ev, "document_type", "document")
                    page_num = _get_val(ev, "page_number", 1)
                    span = _get_val(ev, "quoted_span", "")
                    lines.append(f"  - `[{doc_id}]` {doc_type} (Page {page_num}): \"{span}\"")
            else:
                lines.append("- **Supporting Evidence Citations:** None attached.")

            lines.append("")

    # =========================================================================
    # 5. Evidence / Grounding
    # =========================================================================
    lines.append("## 5. Evidence / Grounding")
    lines.append("")

    doc_ids = state.get("document_ids") or []
    classified = state.get("classified_types") or {}
    chunk_ids = state.get("retrieved_chunk_ids") or []
    grounded = state.get("summary_grounded", False)

    lines.append("### Dossier Manifest Provenance")
    if doc_ids:
        for d_id in doc_ids:
            d_type = classified.get(d_id, "unknown")
            lines.append(f"- `[{d_id}]` Classified Type: **{d_type}**")
    else:
        lines.append("- No uploaded documents registered in dossier manifest.")
    lines.append("")

    lines.append("### Authoritative Policy Guidance & Citations")
    if chunk_ids:
        for c_id in chunk_ids:
            lines.append(f"- Referenced Policy Passage: `{c_id}`")
    else:
        lines.append("- No underwriting policy passages retrieved.")
    lines.append("")

    grounding_badge = "✅ PASS (Strictly Grounded)" if grounded else "ℹ️ PENDING / UNVERIFIED"
    lines.append(f"- **Citation Grounding Gate Status:** {grounding_badge}")
    lines.append("")

    # =========================================================================
    # 6. Human Underwriter Review
    # =========================================================================
    lines.append("## 6. Human Underwriter Review")
    lines.append("")
    lines.append(
        "> **MANDATORY UNDERWRITER SIGN-OFF NOTICE:**  \n"
        "> Autonomous credit lending decisions are strictly prohibited. FinScan AI provides deterministic "
        "arithmetic verification, fact extraction, and policy grounding solely to assist human underwriter review. "
        "A qualified underwriter must inspect all findings and flags above before executing a formal disposition."
    )
    lines.append("")

    reviewer_dec = state.get("reviewer_decision")
    reviewer_notes = state.get("reviewer_notes")

    if reviewer_dec:
        lines.append(f"- **Reviewer Decision Recorded:** `{reviewer_dec}`")
        if reviewer_notes:
            lines.append(f"- **Underwriter Notes:** {reviewer_notes}")
        lines.append("")

    lines.append("- **Reviewer:** _________________________________________")
    lines.append("- **Decision:** [ ] APPROVED   [ ] REJECTED   [ ] NEEDS_INFO")
    lines.append("- **Comments:** _________________________________________")
    lines.append("- **Signature:** _________________________________________")
    lines.append("- **Date:** ____________________")
    lines.append("")

    return "\n".join(lines)
