"""
Identity Rule: Cross-checks applicant name and PAN number across KYC, payslip, and bank statement.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

import re
from typing import List, Optional, Tuple

from rapidfuzz import fuzz

from core.contracts.evidence import EvidenceRef
from core.contracts.facts import ApplicantFact
from core.contracts.findings import Finding

# AGENTS.md RULE-ID-01: fuzzy name match must score >= 85 token_sort_ratio.
NAME_MATCH_THRESHOLD = 85.0
NAME_VARIATION_THRESHOLD = 70.0

COMMON_TITLES = {"mr", "mrs", "ms", "miss", "dr", "shri", "smt", "prof"}

_WHITESPACE = re.compile(r"\s+")
_NAME_NOISE = re.compile(r"[^\w\s]")


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


def normalize_name_tokens(name: Optional[str]) -> str:
    """
    Normalizes a name string by stripping non-alphanumeric characters,
    lowercasing, removing standard honorific titles, and sorting tokens.
    """
    if not name:
        return ""
    cleaned = _NAME_NOISE.sub(" ", str(name).lower())
    tokens = [t for t in cleaned.split() if t]
    if len(tokens) > 1:
        filtered = [t for t in tokens if t not in COMMON_TITLES]
        if filtered:
            tokens = filtered
    return " ".join(sorted(tokens))


def compute_name_similarity(name1: str, name2: str) -> float:
    """
    Computes deterministic token-sorted fuzzy similarity in [0.0, 1.0].
    Uses RapidFuzz token_sort_ratio for high-performance Levenshtein matching.
    """
    norm1 = normalize_name_tokens(name1)
    norm2 = normalize_name_tokens(name2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0
    return float(fuzz.token_sort_ratio(norm1, norm2)) / 100.0


def audit_identity_consistency(
    applicant: Optional[ApplicantFact],
    payslip_name: Optional[str] = None,
    bank_name: Optional[str] = None,
    tax_pan: Optional[str] = None,
    *,
    tax_name: Optional[str] = None,
    pan_to_compare: Optional[str] = None,
    pan_evidence: Optional[EvidenceRef] = None,
    payslip_name_evidence: Optional[EvidenceRef] = None,
    bank_name_evidence: Optional[EvidenceRef] = None,
    tax_name_evidence: Optional[EvidenceRef] = None,
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
            reason="KYC document carries no readable applicant name.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    # 3. Collect supporting evidence from KYC
    evidence: List[EvidenceRef] = []
    src_name = getattr(applicant, "source_name", None)
    if isinstance(src_name, EvidenceRef):
        evidence.append(src_name)
    src_pan = getattr(applicant, "source_pan", None)
    if isinstance(src_pan, EvidenceRef):
        evidence.append(src_pan)
    if pan_evidence:
        evidence.append(pan_evidence)

    # 4. PAN consistency verification (if PAN comparison requested)
    target_pan = tax_pan if tax_pan is not None else pan_to_compare
    pan_checked = False
    pan_matches = True
    norm_kyc_pan = normalize_pan(applicant.pan_number)
    norm_doc_pan = normalize_pan(target_pan) if target_pan is not None else None

    if target_pan is not None and target_pan.strip():
        pan_checked = True
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

        pan_matches = norm_kyc_pan == norm_doc_pan
        if not pan_matches:
            return Finding(
                rule_id="RULE-ID-01",
                rule_name="Cross-Document Identity Consistency",
                verdict="flag",
                reason=f"Critical identity mismatch: KYC PAN '{applicant.pan_number}' does not match document PAN '{target_pan}'.",
                supporting_evidence=evidence,
                policy_version="v1.0",
            )

    # 5. Collect document names to cross-check, keeping each side's own
    # page evidence. A finding that names a document in prose MUST cite that
    # document's page, otherwise cross-document evidence shows KYC twice.
    docs_to_compare: List[Tuple[str, str, Optional[EvidenceRef]]] = []
    if payslip_name and str(payslip_name).strip().upper() != "UNKNOWN":
        docs_to_compare.append(("payslip", str(payslip_name).strip(), payslip_name_evidence))
    if bank_name and str(bank_name).strip().upper() != "UNKNOWN":
        docs_to_compare.append(("bank statement", str(bank_name).strip(), bank_name_evidence))
    if tax_name and str(tax_name).strip().upper() != "UNKNOWN":
        docs_to_compare.append(("tax return", str(tax_name).strip(), tax_name_evidence))
    for _, _, doc_ev in docs_to_compare:
        if isinstance(doc_ev, EvidenceRef):
            evidence.append(doc_ev)

    if not docs_to_compare and not pan_checked:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason=(
                f"No secondary document available to verify identity of {applicant.full_name}: "
                "payslip name, bank account holder, and ITR PAN are all absent."
            ),
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    # 6. Evaluate fuzzy similarity per policy thresholds
    flag_critical: List[str] = []
    flag_variation: List[str] = []
    verified_matches: List[str] = []
    scores: List[float] = []

    for doc_label, doc_val, _doc_ev in docs_to_compare:
        sim = compute_name_similarity(applicant_name, doc_val)
        score_pct = sim * 100.0
        scores.append(score_pct)

        if score_pct < NAME_VARIATION_THRESHOLD:
            flag_critical.append(f"{doc_label} names '{doc_val}' ({score_pct:.0f}% match, below {NAME_MATCH_THRESHOLD:.0f}%)")
        elif score_pct < NAME_MATCH_THRESHOLD:
            flag_variation.append(f"{doc_label} names '{doc_val}' ({score_pct:.0f}% match, below {NAME_MATCH_THRESHOLD:.0f}%)")
        else:
            verified_matches.append(doc_label)

    if flag_critical:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="flag",
            reason=f"Critical identity mismatch against KYC applicant '{applicant_name}': {'; '.join(flag_critical)}.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    if flag_variation:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="flag",
            reason=f"Reviewer verification required for name variation against KYC applicant '{applicant_name}': {'; '.join(flag_variation)}.",
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    verified = list(verified_matches)
    if pan_checked and pan_matches:
        verified.append("ITR PAN")

    lowest_str = f" (lowest name match {min(scores):.0f}%)" if scores else ""
    return Finding(
        rule_id="RULE-ID-01",
        rule_name="Cross-Document Identity Consistency",
        verdict="pass",
        reason=f"Identity confirmed for {applicant_name} across {', '.join(verified)}{lowest_str}.",
        supporting_evidence=evidence,
        policy_version="v1.0",
    )
