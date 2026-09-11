"""
Summary assembly and Credit Appraisal Memo generation.

The memo is assembled deterministically from rule findings and retrieved policy
chunk IDs. No number, verdict, or disposition in this narrative originates from
an LLM — it only restates what core/rules/ already computed (AGENTS.md §1).
"""

from typing import Any, List

from core.contracts.state import LoanApplicationState

_VERDICT_BADGES = {
    "pass": "✅ PASS",
    "flag": "⚠️ FLAG",
    "unknown": "❓ UNKNOWN",
}


def _finding_field(finding: Any, name: str, default: Any = None) -> Any:
    """Reads a field from a Finding model or its serialized dict form."""
    if isinstance(finding, dict):
        return finding.get(name, default)
    return getattr(finding, name, default)


def build_appraisal_memo(state: LoanApplicationState) -> str:
    """
    Assembles the cited Credit Appraisal Memo markdown from deterministic state.

    Bracketed policy IDs are machine-parseable: validate_grounding_node extracts
    them and rejects any citation outside retrieved_chunk_ids, so the citation
    line format here is load-bearing for the grounding gate.
    """
    app_id = state.get("application_id", "APP-UNKNOWN")
    applicant = state.get("applicant")
    applicant_name = applicant.full_name if applicant else "Unknown Applicant"
    findings = state.get("findings", [])
    chunks = state.get("retrieved_chunk_ids", [])
    missing_docs = state.get("missing_documents", [])

    summary_lines: List[str] = [
        f"### Credit Appraisal Memo — {app_id}",
        f"**Applicant Name:** {applicant_name}",
        "",
        "#### Deterministic Verification Summary",
    ]
    for finding in findings:
        verdict = _finding_field(finding, "verdict")
        status_badge = _VERDICT_BADGES.get(verdict, _VERDICT_BADGES["unknown"])
        rule_name = _finding_field(finding, "rule_name")
        rule_id = _finding_field(finding, "rule_id")
        reason = _finding_field(finding, "reason")
        summary_lines.append(f"- **{rule_name}** ({rule_id}) [{status_badge}]: {reason}")

    if missing_docs:
        summary_lines.append("")
        summary_lines.append(f"**Missing Mandatory Documents:** {', '.join(missing_docs)}")

    summary_lines.append("")
    summary_lines.append("#### Authoritative Policy Citations")
    summary_lines.append(f"Referenced guidelines: {', '.join(f'[{c}]' for c in chunks) if chunks else 'None'}")

    return "\n".join(summary_lines)
