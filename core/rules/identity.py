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

COMMON_TITLES = {"mr", "mrs", "ms", "miss", "dr", "shri", "smt", "prof"}


def normalize_pan(pan: Optional[str]) -> Optional[str]:
    """
    Normalizes a PAN string by stripping whitespace, hyphens, underscores,
    and converting to uppercase.
    Returns None if pan is None, empty, or 'UNKNOWN'.
    """
    if not pan:
        return None
    cleaned = re.sub(r"[\s\-_]", "", str(pan).strip()).upper()
    if not cleaned or cleaned == "UNKNOWN":
        return None
    return cleaned


def normalize_name_tokens(name: str) -> str:
    """
    Normalizes a name string by stripping non-alphanumeric characters,
    lowercasing, removing standard honorific titles, and sorting individual
    tokens alphabetically for word-order invariance.
    """
    if not name:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    tokens = [token for token in cleaned.split() if token]
    if len(tokens) > 1:
        filtered = [t for t in tokens if t not in COMMON_TITLES]
        if filtered:
            tokens = filtered
    return " ".join(sorted(tokens))


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
    payslip_name: Optional[str] = None,
    bank_name: Optional[str] = None,
    pan_to_compare: Optional[str] = None,
    *,
    pan_evidence: Optional[EvidenceRef] = None,
    tax_name: Optional[str] = None,
    tax_pan: Optional[str] = None,
) -> Finding:
    """
    RULE-ID-01: Cross-checks applicant name and PAN number across KYC, payslip,
    bank statement, and tax records.
    Deterministic Python only. No LLM involvement.

    Policy thresholds (per kyc_guidelines_v1.md):
      - Fuzzy match >= 85%: pass
      - Fuzzy match 70% - 84%: flag ("Reviewer verification required for name variation")
      - Fuzzy match < 70%: flag ("Critical identity mismatch")
      - PAN mismatch: flag ("Critical identity mismatch")
      - Missing applicant, missing readable name, or missing compared PAN: unknown
    """
    # 1. Check primary applicant KYC document presence
    if applicant is None:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="Missing primary applicant KYC document.",
            supporting_evidence=[],
            policy_version="v1.0",
        )

    # 2. Validate that applicant has a readable name
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

    # 3. Collect supporting evidence from KYC
    evidence: List[EvidenceRef] = []
    if getattr(applicant, "source_name", None):
        evidence.append(applicant.source_name)
    if getattr(applicant, "source_pan", None):
        evidence.append(applicant.source_pan)
    if pan_evidence:
        evidence.append(pan_evidence)

    # 4. PAN consistency verification (if PAN comparison requested)
    target_pan = tax_pan if tax_pan is not None else pan_to_compare
    if target_pan is not None:
        norm_kyc_pan = normalize_pan(applicant.pan_number)
        norm_doc_pan = normalize_pan(target_pan)

        if norm_kyc_pan is None:
            return Finding(
                rule_id="RULE-ID-01",
                rule_name="Cross-Document Identity Consistency",
                verdict="unknown",
                reason="Cannot verify PAN consistency: KYC PAN is missing or unknown.",
                supporting_evidence=evidence,
                policy_version="v1.0",
            )

        if norm_doc_pan is None:
            return Finding(
                rule_id="RULE-ID-01",
                rule_name="Cross-Document Identity Consistency",
                verdict="unknown",
                reason="Cannot verify PAN consistency: Comparison document PAN is missing or unknown.",
                supporting_evidence=evidence,
                policy_version="v1.0",
            )

        if norm_kyc_pan != norm_doc_pan:
            return Finding(
                rule_id="RULE-ID-01",
                rule_name="Cross-Document Identity Consistency",
                verdict="flag",
                reason=f"Critical identity mismatch: KYC PAN '{applicant.pan_number}' does not match document PAN '{target_pan}'.",
                supporting_evidence=evidence,
                policy_version="v1.0",
            )

    # 5. Collect document names to cross-check
    docs_to_compare: List[Tuple[str, str]] = []
    if payslip_name and str(payslip_name).strip().upper() != "UNKNOWN":
        docs_to_compare.append(("Payslip", str(payslip_name).strip()))
    if bank_name and str(bank_name).strip().upper() != "UNKNOWN":
        docs_to_compare.append(("Bank statement", str(bank_name).strip()))
    if tax_name and str(tax_name).strip().upper() != "UNKNOWN":
        docs_to_compare.append(("Tax return", str(tax_name).strip()))

    if not docs_to_compare:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="Cannot verify identity: Payslip and bank statement account holder names are missing or unknown.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    # 6. Evaluate fuzzy similarity per policy thresholds
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

    pan_status = f", PAN confirmed ({normalize_pan(applicant.pan_number)})" if target_pan is not None else ""
    return Finding(
        rule_id="RULE-ID-01",
        rule_name="Cross-Document Identity Consistency",
        verdict="pass",
        reason=f"Identity confirmed across documents for {applicant_name}{pan_status} ({'; '.join(verified_matches)}).",
        supporting_evidence=evidence,
        policy_version="v1.0",
    )
