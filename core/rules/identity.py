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

_WHITESPACE = re.compile(r"\s+")
_NAME_NOISE = re.compile(r"[^A-Z\s]")


def _normalize_name(value: Optional[str]) -> str:
    """Uppercase, strip punctuation/honorific dots, and collapse whitespace."""
    if not value:
        return ""
    cleaned = _NAME_NOISE.sub(" ", value.upper())
    return _WHITESPACE.sub(" ", cleaned).strip()


def _normalize_pan(value: Optional[str]) -> str:
    if not value:
        return ""
    return _WHITESPACE.sub("", value.upper())


def audit_identity_consistency(
    applicant: Optional[ApplicantFact],
    payslip_name: Optional[str],
    bank_name: Optional[str],
    tax_pan: Optional[str] = None,
) -> Finding:
    """
    Verifies the KYC applicant identity holds across payslip, bank statement, and ITR.

    Names are compared with RapidFuzz token_sort_ratio so word order and middle-name
    variation do not cause false flags. PAN is compared exactly after normalisation.
    If the KYC document or every comparison source is missing, verdict MUST be 'unknown'.
    """
    if applicant is None:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="Missing primary applicant KYC document.",
            policy_version="v1.0",
        )

    kyc_name = _normalize_name(applicant.full_name)
    if not kyc_name:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="KYC document carries no readable applicant name.",
            supporting_evidence=[applicant.source_name],
            policy_version="v1.0",
        )

    evidence: List[EvidenceRef] = [applicant.source_name]

    # 1. Fuzzy name comparison against every available secondary document.
    scored: List[Tuple[str, str, float]] = []
    for label, candidate in (("payslip", payslip_name), ("bank statement", bank_name)):
        normalized = _normalize_name(candidate)
        if normalized:
            scored.append((label, candidate.strip(), fuzz.token_sort_ratio(kyc_name, normalized)))

    # 2. PAN cross-check against the ITR filing.
    pan_checked = False
    pan_matches = True
    kyc_pan = _normalize_pan(applicant.pan_number)
    itr_pan = _normalize_pan(tax_pan)
    if kyc_pan and itr_pan:
        pan_checked = True
        pan_matches = kyc_pan == itr_pan
        if applicant.source_pan is not None:
            evidence.append(applicant.source_pan)

    if not scored and not pan_checked:
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

    problems: List[str] = []
    for label, raw, score in scored:
        if score < NAME_MATCH_THRESHOLD:
            problems.append(f"{label} names '{raw}' ({score:.0f}% match, below {NAME_MATCH_THRESHOLD:.0f}%)")
    if pan_checked and not pan_matches:
        problems.append(f"ITR PAN {itr_pan} does not match KYC PAN {kyc_pan}")

    if problems:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="flag",
            reason=(
                f"Identity mismatch against KYC applicant '{applicant.full_name}': " + "; ".join(problems) + "."
            ),
            supporting_evidence=evidence,
            policy_version="v1.0",
        )

    verified = [label for label, _, _ in scored]
    if pan_checked:
        verified.append("ITR PAN")
    return Finding(
        rule_id="RULE-ID-01",
        rule_name="Cross-Document Identity Consistency",
        verdict="pass",
        reason=(
            f"Identity confirmed for {applicant.full_name} across {', '.join(verified)}"
            + (f" (lowest name match {min(s for _, _, s in scored):.0f}%)." if scored else ".")
        ),
        supporting_evidence=evidence,
        policy_version="v1.0",
    )
