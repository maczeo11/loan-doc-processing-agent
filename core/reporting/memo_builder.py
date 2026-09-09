"""
Credit Appraisal Memo (CAM) Builder.
HUMAN-ONLY ZONE: Owned by Member 4 (Sravanthi).

Generates an auditable, structured Credit Appraisal Memo (CAM) in Markdown and structured dict format.
Prime Invariants:
  1. Deterministic code decides. AI explains. A human approves.
  2. Every number traces back to a page in a document.
  3. Zero financial values are invented, guessed, or hallucinated.
  4. Mandatory PII masking for PAN and bank account numbers.
  5. Missing or unverifiable values remain UNKNOWN (never zero).
  6. Zero lending approval or rejection decisions made autonomously.
  7. Strict provenance preservation for all extracted facts with EvidenceRefs.
"""

import re
from typing import Any, Dict, List, Optional, Union
from core.contracts.state import LoanApplicationState
from core.contracts.findings import Finding


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
    Returns 'UNKNOWN' if missing, null, or invalid.
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


def _extract_evidence_ref(fact_obj: Any) -> Optional[Any]:
    """Extracts the underlying EvidenceRef source from a fact or MoneyFact."""
    if fact_obj is None:
        return None
    if isinstance(fact_obj, dict):
        return fact_obj.get("source")
    return getattr(fact_obj, "source", None)


def _format_evidence_citation(ev: Any) -> Optional[str]:
    """Formats an EvidenceRef or dict into a concise audit citation."""
    if ev is None:
        return None
    doc_id = _get_val(ev, "document_id", "DOC")
    doc_type = _get_val(ev, "document_type", "document")
    page_num = _get_val(ev, "page_number", 1)
    span = _get_val(ev, "quoted_span", "")
    return f"`[{doc_id}]` {doc_type} (Page {page_num}): \"{span}\""


def build_appraisal_summary(
    state: Union[LoanApplicationState, Dict[str, Any]],
    manifest: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Builds a structured, deterministic dictionary summarizing the dossier,
    findings (split by PASS/FLAG/UNKNOWN), applicant facts, financial facts,
    and documents checked.
    """
    app_id = _get_val(state, "application_id", "UNKNOWN")
    status = _get_val(state, "status", "READY_FOR_REVIEW")
    raw_findings = _get_val(state, "findings", []) or []
    missing_docs = _get_val(state, "missing_documents", []) or []
    doc_ids = _get_val(state, "document_ids", []) or []
    classified = _get_val(state, "classified_types", {}) or {}
    chunk_ids = _get_val(state, "retrieved_chunk_ids", []) or []
    grounded = bool(_get_val(state, "summary_grounded", False))

    pass_findings: List[Dict[str, Any]] = []
    flag_findings: List[Dict[str, Any]] = []
    unknown_findings: List[Dict[str, Any]] = []
    all_findings: List[Dict[str, Any]] = []

    for f in raw_findings:
        rule_id = _get_val(f, "rule_id", "RULE-UNKNOWN")
        rule_name = _get_val(f, "rule_name", "Verification Rule")
        verdict = str(_get_val(f, "verdict", "unknown")).lower().strip()
        reason = _get_val(f, "reason", "")
        policy_ver = _get_val(f, "policy_version", "v1.0")
        ev_list = _get_val(f, "supporting_evidence", []) or []

        f_dict = {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "verdict": verdict,
            "reason": reason,
            "policy_version": policy_ver,
            "supporting_evidence": [
                {
                    "document_id": _get_val(ev, "document_id", "DOC"),
                    "document_type": _get_val(ev, "document_type", "document"),
                    "page_number": _get_val(ev, "page_number", 1),
                    "quoted_span": _get_val(ev, "quoted_span", ""),
                }
                for ev in ev_list
            ],
        }
        all_findings.append(f_dict)
        if verdict == "pass":
            pass_findings.append(f_dict)
        elif verdict == "flag":
            flag_findings.append(f_dict)
        else:
            unknown_findings.append(f_dict)

    # Applicant details
    app_obj = _get_val(state, "applicant")
    applicant_summary = {
        "full_name": _get_val(app_obj, "full_name") or "UNKNOWN",
        "dob": _get_val(app_obj, "dob") or "UNKNOWN",
        "pan_masked": mask_pan(_get_val(app_obj, "pan_number")),
        "aadhaar_masked": mask_aadhaar(_get_val(app_obj, "aadhaar_masked")),
        "source_name": _format_evidence_citation(_get_val(app_obj, "source_name")),
        "source_pan": _format_evidence_citation(_get_val(app_obj, "source_pan")),
    }

    # Financial details
    ps_obj = _get_val(state, "payslip")
    bs_obj = _get_val(state, "bank_statement")
    tr_obj = _get_val(state, "tax_return")

    gross_fact = _get_val(ps_obj, "gross_salary")
    net_fact = _get_val(ps_obj, "net_salary")
    ded_fact = _get_val(ps_obj, "deductions_total")
    close_fact = _get_val(bs_obj, "closing_balance")
    avg_sal_fact = _get_val(bs_obj, "average_salary_credit")
    itr_gross_fact = _get_val(tr_obj, "gross_total_income")
    tax_paid_fact = _get_val(tr_obj, "total_tax_paid")

    financial_summary = {
        "payslip": {
            "employer_name": _get_val(ps_obj, "employer_name") or "UNKNOWN",
            "pay_period": _get_val(ps_obj, "pay_period_str") or "UNKNOWN",
            "gross_salary": _format_money(gross_fact),
            "gross_salary_citation": _format_evidence_citation(_extract_evidence_ref(gross_fact)),
            "net_salary": _format_money(net_fact),
            "net_salary_citation": _format_evidence_citation(_extract_evidence_ref(net_fact)),
            "deductions_total": _format_money(ded_fact),
            "deductions_citation": _format_evidence_citation(_extract_evidence_ref(ded_fact)),
        },
        "bank_statement": {
            "bank_name": _get_val(bs_obj, "bank_name") or "UNKNOWN",
            "account_holder": _get_val(bs_obj, "account_holder") or "UNKNOWN",
            "account_number_masked": mask_account_number(_get_val(bs_obj, "account_number_masked")),
            "closing_balance": _format_money(close_fact),
            "closing_balance_citation": _format_evidence_citation(_extract_evidence_ref(close_fact)),
            "average_salary_credit": _format_money(avg_sal_fact),
            "average_salary_credit_citation": _format_evidence_citation(_extract_evidence_ref(avg_sal_fact)),
            "bounced_transactions": _get_val(bs_obj, "bounced_transactions", 0),
        },
        "tax_return": {
            "assessee_name": _get_val(tr_obj, "assessee_name") or "UNKNOWN",
            "pan_masked": mask_pan(_get_val(tr_obj, "pan_number")),
            "assessment_year": _get_val(tr_obj, "assessment_year") or "UNKNOWN",
            "gross_total_income": _format_money(itr_gross_fact),
            "gross_total_income_citation": _format_evidence_citation(_extract_evidence_ref(itr_gross_fact)),
            "total_tax_paid": _format_money(tax_paid_fact),
            "total_tax_paid_citation": _format_evidence_citation(_extract_evidence_ref(tax_paid_fact)),
        },
    }

    # Ground truth reference (if manifest is supplied)
    manifest_data = manifest or _get_val(state, "manifest") or _get_val(state, "dossier_manifest")
    gt_summary = None
    if manifest_data:
        gt_summary = {
            "scenario": manifest_data.get("scenario", "UNKNOWN"),
            "expected_rule_outcomes": manifest_data.get("expected_rule_outcomes", {}),
            "financial_ground_truth": manifest_data.get("financial_ground_truth", {}),
            "is_extracted_evidence": False,
        }

    return {
        "application_id": app_id,
        "status": status,
        "applicant_summary": applicant_summary,
        "financial_summary": financial_summary,
        "documents_checked": {
            "total_uploaded": len(doc_ids),
            "document_ids": list(doc_ids),
            "classified_types": dict(classified),
            "missing_documents": list(missing_docs),
        },
        "counts": {
            "total": len(all_findings),
            "pass": len(pass_findings),
            "flag": len(flag_findings),
            "unknown": len(unknown_findings),
        },
        "all_findings": all_findings,
        "pass_findings": pass_findings,
        "flag_findings": flag_findings,
        "unknown_findings": unknown_findings,
        "policy_citations": list(chunk_ids),
        "grounding_status": grounded,
        "manifest_ground_truth": gt_summary,
    }


def build_appraisal_memo(
    state: Union[LoanApplicationState, Dict[str, Any]],
    manifest: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Assembles a comprehensive, auditable Credit Appraisal Memo (CAM) in Markdown.
    Contains 6 mandatory sections:
      1. Executive Summary (with verdict counts and documents checked)
      2. Applicant Details (with PII masking and identity provenance citations)
      3. Financial Analysis (payslip, bank statement, tax facts with EvidenceRef provenance)
      4. Rule Findings (verdict breakdown: PASS, FLAG, UNKNOWN, followed by full details)
      5. Evidence / Grounding (provenance, policy guidelines, grounding gate status)
      6. Human Underwriter Review (sign-off block; autonomous decisions strictly prohibited)

    Invariants:
      - Zero hallucinated numbers: every figure originates from facts or is UNKNOWN.
      - Zero new financial calculations or decisions.
      - Every finding's verdict, reason, and citations are preserved verbatim.
    """
    app_id = _get_val(state, "application_id", "UNKNOWN")
    status = _get_val(state, "status", "READY_FOR_REVIEW")
    findings: List[Union[Finding, Dict[str, Any]]] = _get_val(state, "findings", []) or []
    missing_docs: List[str] = _get_val(state, "missing_documents", []) or []
    doc_ids = _get_val(state, "document_ids", []) or []
    classified = _get_val(state, "classified_types", {}) or {}
    chunk_ids = _get_val(state, "retrieved_chunk_ids", []) or []
    grounded = bool(_get_val(state, "summary_grounded", False))

    applicant_data = _get_val(state, "applicant")
    payslip_data = _get_val(state, "payslip")
    bank_data = _get_val(state, "bank_statement")
    tax_data = _get_val(state, "tax_return")

    # Partition findings
    pass_count = 0
    flag_count = 0
    unknown_count = 0
    pass_list = []
    flag_list = []
    unknown_list = []

    for f in findings:
        v = str(_get_val(f, "verdict", "unknown")).lower().strip()
        if v == "pass":
            pass_count += 1
            pass_list.append(f)
        elif v == "flag":
            flag_count += 1
            flag_list.append(f)
        else:
            unknown_count += 1
            unknown_list.append(f)

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
    lines.append(f"- **Documents Uploaded / Checked:** {len(doc_ids)} registered")

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

    source_pan_ev = _get_val(applicant_data, "source_pan")
    if source_pan_ev and source_pan_ev != source_name_ev:
        doc_id = _get_val(source_pan_ev, "document_id", "KYC")
        page_num = _get_val(source_pan_ev, "page_number", 1)
        span = _get_val(source_pan_ev, "quoted_span", "")
        lines.append(f"- **PAN Source Citation:** `[{doc_id}]` Page {page_num} (Quoted: \"{span}\")")

    lines.append("")

    # =========================================================================
    # 3. Financial Analysis
    # =========================================================================
    lines.append("## 3. Financial Analysis")
    lines.append("")

    gross_salary_fact = _get_val(payslip_data, "gross_salary")
    gross_salary_val = _format_money(gross_salary_fact)
    gross_ev = _extract_evidence_ref(gross_salary_fact)

    net_salary_fact = _get_val(payslip_data, "net_salary")
    net_salary_val = _format_money(net_salary_fact)
    net_ev = _extract_evidence_ref(net_salary_fact)

    deductions_fact = _get_val(payslip_data, "deductions_total")
    deductions_val = _format_money(deductions_fact)
    ded_ev = _extract_evidence_ref(deductions_fact)

    pay_period_val = _get_val(payslip_data, "pay_period_str") or "UNKNOWN"

    bank_name_val = _get_val(bank_data, "bank_name") or "UNKNOWN"
    acct_holder_val = _get_val(bank_data, "account_holder") or "UNKNOWN"
    acct_no_masked = mask_account_number(_get_val(bank_data, "account_number_masked"))

    avg_salary_fact = _get_val(bank_data, "average_salary_credit")
    avg_salary_credit_val = _format_money(avg_salary_fact)
    avg_sal_ev = _extract_evidence_ref(avg_salary_fact)

    closing_bal_fact = _get_val(bank_data, "closing_balance")
    closing_bal_val = _format_money(closing_bal_fact)
    closing_ev = _extract_evidence_ref(closing_bal_fact)

    bounced_count = _get_val(bank_data, "bounced_transactions", "UNKNOWN")

    assessee_val = _get_val(tax_data, "assessee_name") or "UNKNOWN"
    ay_val = _get_val(tax_data, "assessment_year") or "UNKNOWN"

    itr_gross_fact = _get_val(tax_data, "gross_total_income")
    itr_gross_val = _format_money(itr_gross_fact)
    itr_gross_ev = _extract_evidence_ref(itr_gross_fact)

    tax_paid_fact = _get_val(tax_data, "total_tax_paid")
    tax_paid_val = _format_money(tax_paid_fact)
    tax_paid_ev = _extract_evidence_ref(tax_paid_fact)

    lines.append("### Payslip Financial Facts")
    lines.append(f"- **Pay Period:** {pay_period_val}")
    lines.append(f"- **Gross Monthly Salary:** {gross_salary_val}")
    if gross_ev:
        lines.append(f"  - *Evidence:* {_format_evidence_citation(gross_ev)}")
    lines.append(f"- **Net Take-Home Salary:** {net_salary_val}")
    if net_ev:
        lines.append(f"  - *Evidence:* {_format_evidence_citation(net_ev)}")
    lines.append(f"- **Total Deductions:** {deductions_val}")
    if ded_ev:
        lines.append(f"  - *Evidence:* {_format_evidence_citation(ded_ev)}")
    lines.append("")

    lines.append("### Bank Statement Financial Facts")
    lines.append(f"- **Bank Name:** {bank_name_val}")
    lines.append(f"- **Account Holder:** {acct_holder_val}")
    lines.append(f"- **Account Number (Masked):** `{acct_no_masked}`")
    lines.append(f"- **Average Monthly Salary Credit:** {avg_salary_credit_val}")
    if avg_sal_ev:
        lines.append(f"  - *Evidence:* {_format_evidence_citation(avg_sal_ev)}")
    lines.append(f"- **Closing Account Balance:** {closing_bal_val}")
    if closing_ev:
        lines.append(f"  - *Evidence:* {_format_evidence_citation(closing_ev)}")
    lines.append(f"- **Bounced Transactions Count:** {bounced_count}")
    lines.append("")

    lines.append("### Income Tax Return (ITR-V) Facts")
    lines.append(f"- **Assessee Name:** {assessee_val}")
    lines.append(f"- **Assessment Year:** {ay_val}")
    lines.append(f"- **Gross Total Annual Income:** {itr_gross_val}")
    if itr_gross_ev:
        lines.append(f"  - *Evidence:* {_format_evidence_citation(itr_gross_ev)}")
    lines.append(f"- **Total Tax Paid:** {tax_paid_val}")
    if tax_paid_ev:
        lines.append(f"  - *Evidence:* {_format_evidence_citation(tax_paid_ev)}")
    lines.append("")

    # =========================================================================
    # 4. Rule Findings
    # =========================================================================
    lines.append("## 4. Rule Findings")
    lines.append("")

    if not findings:
        lines.append("No deterministic rule findings have been evaluated.")
    else:
        # Grouped summary by verdict
        lines.append("### Findings Verdict Grouping")
        lines.append("")

        # FLAG findings
        lines.append("#### ⚠️ Flagged Findings (Attention Required)")
        if flag_list:
            for f in flag_list:
                r_id = _get_val(f, "rule_id", "RULE")
                r_name = _get_val(f, "rule_name", "Verification Rule")
                r_reason = _get_val(f, "reason", "")
                lines.append(f"- **{r_id} ({r_name}):** {r_reason}")
        else:
            lines.append("- None (No discrepancies flagged).")
        lines.append("")

        # PASS findings
        lines.append("#### ✅ Passed Findings (Verified)")
        if pass_list:
            for f in pass_list:
                r_id = _get_val(f, "rule_id", "RULE")
                r_name = _get_val(f, "rule_name", "Verification Rule")
                r_reason = _get_val(f, "reason", "")
                lines.append(f"- **{r_id} ({r_name}):** {r_reason}")
        else:
            lines.append("- None.")
        lines.append("")

        # UNKNOWN findings
        lines.append("#### ❓ Unknown Findings (Information Needed / Incomplete)")
        if unknown_list:
            for f in unknown_list:
                r_id = _get_val(f, "rule_id", "RULE")
                r_name = _get_val(f, "rule_name", "Verification Rule")
                r_reason = _get_val(f, "reason", "")
                lines.append(f"- **{r_id} ({r_name}):** {r_reason}")
        else:
            lines.append("- None.")
        lines.append("")

        # Detailed breakdown per rule
        lines.append("### Detailed Rule Evaluation")
        lines.append("")

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

    # Optional Ground Truth Manifest Context (clearly demarcated as benchmark only)
    manifest_data = manifest or _get_val(state, "manifest") or _get_val(state, "dossier_manifest")
    if manifest_data and isinstance(manifest_data, dict) and "scenario" in manifest_data:
        scenario = manifest_data.get("scenario", "UNKNOWN")
        expected_outcomes = manifest_data.get("expected_rule_outcomes", {})
        lines.append("### Dossier Manifest Reference (Synthetic Benchmark — Non-Extracted Context)")
        lines.append(
            "> **Audit Benchmark Note:** The following baseline metadata is supplied by the synthetic dossier "
            "manifest for audit comparison. It represents ground truth test parameters and does NOT constitute "
            "extracted document evidence unless an explicit EvidenceRef is attached."
        )
        lines.append(f"- **Generation Scenario:** `{scenario}`")
        if expected_outcomes:
            outcomes_str = ", ".join(f"{k}: {v}" for k, v in expected_outcomes.items())
            lines.append(f"- **Benchmark Expected Outcomes:** `{outcomes_str}`")
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

    reviewer_dec = _get_val(state, "reviewer_decision")
    reviewer_notes = _get_val(state, "reviewer_notes")

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
