"""
Identity Rule: Cross-checks applicant name and PAN number across KYC, payslip, and bank statement.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

import difflib
import re
from typing import Optional, List, Tuple
from core.contracts.findings import Finding
from core.contracts.facts import ApplicantFact
from core.contracts.evidence import EvidenceRef


def normalize_name_tokens(name: str) -> str:
    """
    Normalizes a name string by stripping non-alphanumeric characters,
    lowercasing, and sorting individual tokens alphabetically.
    """
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    tokens = sorted(token for token in cleaned.split() if token)
    return " ".join(tokens)


def compute_name_similarity(name1: str, name2: str) -> float:
    """
    Computes deterministic token-normalized fuzzy similarity ratio in [0.0, 1.0].
    Uses difflib.SequenceMatcher on sorted token strings.
    """
    norm1 = normalize_name_tokens(name1)
    norm2 = normalize_name_tokens(name2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0
    return difflib.SequenceMatcher(None, norm1, norm2).ratio()


def audit_identity_consistency(
    applicant: Optional[ApplicantFact],
    payslip_name: Optional[str],
    bank_name: Optional[str],
    pan_to_compare: Optional[str] = None,
) -> Finding:
    """
    RULE-ID-01: Cross-checks applicant name and PAN number across KYC, payslip, and bank statement.
    Policy thresholds (per kyc_guidelines_v1.md):
      - Fuzzy match >= 85%: pass
      - Fuzzy match 70% - 84%: flag ("Reviewer verification required for name variation")
      - Fuzzy match < 70%: flag ("Critical identity mismatch")
      - PAN mismatch: flag ("Critical identity mismatch")
      - Missing applicant or required data: unknown
    """
    if applicant is None:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="Missing primary applicant KYC document.",
            supporting_evidence=[],
            policy_version="v1.0",
        )

    # Validate that applicant has a readable name
    applicant_name = applicant.full_name.strip() if applicant.full_name else ""
    if not applicant_name or applicant_name.upper() == "UNKNOWN":
        evidence: List[EvidenceRef] = [applicant.source_name] if applicant.source_name else []
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="Applicant KYC document missing readable full name.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    # Collect supporting evidence
    evidence: List[EvidenceRef] = []
    if applicant.source_name:
        evidence.append(applicant.source_name)
    if applicant.source_pan:
        evidence.append(applicant.source_pan)

    # Optional PAN consistency check if comparing against another document PAN
    if pan_to_compare is not None and applicant.pan_number:
        kyc_pan = applicant.pan_number.strip().upper()
        doc_pan = pan_to_compare.strip().upper()
        if kyc_pan != "UNKNOWN" and doc_pan != "UNKNOWN" and kyc_pan != doc_pan:
            return Finding(
                rule_id="RULE-ID-01",
                rule_name="Cross-Document Identity Consistency",
                verdict="flag",
                reason=f"Critical identity mismatch: KYC PAN '{kyc_pan}' does not match document PAN '{doc_pan}'.",
                supporting_evidence=evidence,
                policy_version="v1.0",
            )

    # Collect document names to cross-check
    docs_to_compare: List[Tuple[str, str]] = []
    if payslip_name and payslip_name.strip().upper() != "UNKNOWN":
        docs_to_compare.append(("Payslip", payslip_name.strip()))
    if bank_name and bank_name.strip().upper() != "UNKNOWN":
        docs_to_compare.append(("Bank statement", bank_name.strip()))

    if not docs_to_compare:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="Cannot verify identity: Payslip and bank statement account holder names are missing or unknown.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    flag_critical: List[str] = []
    flag_variation: List[str] = []
    verified_matches: List[str] = []

    for doc_label, doc_val in docs_to_compare:
        score = compute_name_similarity(applicant_name, doc_val)
        score_pct = score * 100.0

        if score < 0.70:
            flag_critical.append(f"{doc_label} name '{doc_val}' vs KYC '{applicant_name}' ({score_pct:.1f}%)")
        elif score < 0.85:
            flag_variation.append(f"{doc_label} name '{doc_val}' vs KYC '{applicant_name}' ({score_pct:.1f}%)")
        else:
            verified_matches.append(f"{doc_label} name '{doc_val}' ({score_pct:.1f}%)")

    if flag_critical:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="flag",
            reason=f"Critical identity mismatch: {'; '.join(flag_critical)}.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    if flag_variation:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="flag",
            reason=f"Reviewer verification required for name variation: {'; '.join(flag_variation)}.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    return Finding(
        rule_id="RULE-ID-01",
        rule_name="Cross-Document Identity Consistency",
        verdict="pass",
        reason=f"Identity confirmed across documents for {applicant_name} ({'; '.join(verified_matches)}).",
        supporting_evidence=evidence,
        policy_version="v1.0",
    )
