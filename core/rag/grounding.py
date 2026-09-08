"""
Grounding Validation & Prompt-Injection Defense.
HUMAN-ONLY ZONE: Validated by Member 8 (Sai Mokshith).

Invariants & Guarantees from AGENTS.md:
- Deterministic citation validation: every claim in CAM must cite authorized chunk IDs.
- Zero Hallucinated Decisions: unsupported claims are dropped; summary abstains if evidence missing.
- Prompt Injection Defense: untrusted document text is sanitized against adversarial override attempts.
"""

import logging
import re
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger("finscan.rag.grounding")

# Canonical aliases recognized across pipeline
CANONICAL_POLICY_ALIASES = {
    "credit_policy_v1_p1": {"CHUNK-POLICY-SAL-02", "CHUNK-POLICY-TAX-03", "credit_policy_v1_p1_c0"},
    "credit_policy_v1_p2": {"CHUNK-POLICY-REQ-01", "credit_policy_v1_p2_c0"},
    "kyc_guidelines_v1_p1": {"CHUNK-POLICY-KYC-01", "kyc_guidelines_v1_p1_c0"},
}

# Adversarial prompt-injection patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"\b(system\s+override|ignore\s+(all\s+)?previous\s+(rules|instructions|prompts))\b", re.IGNORECASE),
    re.compile(r"\b(disregard\s+(all\s+)?(previous\s+)?instructions)\b", re.IGNORECASE),
    re.compile(r"\b(assign\s+pass\s+to\s+all|override\s+all\s+(rules|checks)|bypass\s+credit\s+checks)\b", re.IGNORECASE),
    re.compile(r"\b(you\s+are\s+now\s+in\s+developer\s+mode|jailbreak|dan\s+mode)\b", re.IGNORECASE),
    re.compile(r"\b(new\s+system\s+prompt|print\s+system\s+prompt|reveal\s+instructions)\b", re.IGNORECASE),
    re.compile(r"\b(verdict\s*:\s*pass\s+regardless|force\s+pass|approve\s+unconditionally)\b", re.IGNORECASE),
]


def _expand_authorized_ids(authorized_chunk_ids: List[str]) -> Set[str]:
    """Expands authorized chunk IDs with their recognized aliases."""
    expanded = set(authorized_chunk_ids)
    for primary_id, aliases in CANONICAL_POLICY_ALIASES.items():
        if primary_id in expanded or any(a in expanded for a in aliases):
            expanded.add(primary_id)
            expanded.update(aliases)
    return expanded


def validate_citations(
    claims: List[Dict[str, Any]],
    authorized_chunk_ids: List[str],
) -> bool:
    """
    Asserts every cited chunk ID belongs to the authorized application and retrieved set.
    Unsupported claims are dropped; summary abstains if evidence is missing or invalid.
    """
    if not authorized_chunk_ids:
        logger.warning("Grounding gate rejected: authorized_chunk_ids is empty.")
        return False

    if not claims:
        return False

    authorized_set = _expand_authorized_ids(authorized_chunk_ids)
    valid_citation_found = False

    for claim in claims:
        text = claim.get("text", "").strip()
        citations = claim.get("citations", [])

        # If claim contains no citations
        if not citations:
            # If claim text asserts financial or credit facts without citations, fail
            if any(term in text.lower() for term in ["salary", "inr", "ratio", "dti", "pass", "flag", "approved"]):
                logger.warning(f"Ungrounded financial claim with zero citations: {text[:80]}")
                return False
            continue

        # Check all citations in this claim
        for cit in citations:
            if cit not in authorized_set:
                logger.warning(f"Grounding violation: citation '{cit}' is unauthorized or hallucinated.")
                return False
            valid_citation_found = True

    return valid_citation_found


def filter_grounded_claims(
    claims: List[Dict[str, Any]],
    authorized_chunk_ids: List[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partitions claims into (grounded_claims, dropped_unauthorized_claims).
    Enforces the rule that any statement lacking verified citations is removed.
    """
    authorized_set = _expand_authorized_ids(authorized_chunk_ids)
    grounded: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []

    for claim in claims:
        citations = claim.get("citations", [])
        if citations and all(c in authorized_set for c in citations):
            grounded.append(claim)
        else:
            dropped.append(claim)

    return grounded, dropped


def sanitize_summary_text(
    summary_text: str,
    authorized_chunk_ids: List[str],
) -> str:
    """
    Strips ungrounded statements citing unauthorized chunk IDs and inserts
    explicit abstention notices if evidence is missing.
    """
    if not summary_text:
        return "> ⚠️ [ABSTENTION: Summary empty or missing.]"

    if not authorized_chunk_ids:
        return summary_text + "\n\n> ⚠️ [ABSTENTION: Mandatory supporting evidence missing or unverified.]"

    authorized_set = _expand_authorized_ids(authorized_chunk_ids)
    lines = summary_text.splitlines()
    sanitized_lines: List[str] = []
    has_dropped_claim = False

    for line in lines:
        # Search for citation tags like [DOC_p1] or [credit_policy_v1_p1]
        citation_matches = re.findall(r"\[([a-zA-Z0-9_\-]+)\]", line)
        if citation_matches:
            unauthorized = [c for c in citation_matches if c not in authorized_set and not c.startswith("PASS") and not c.startswith("FLAG") and not c.startswith("UNKNOWN") and not c.startswith("ABSTENTION")]
            if unauthorized:
                has_dropped_claim = True
                sanitized_lines.append(f"> ⚠️ [UNGROUNDED CLAIM DROPPED - Unauthorized citations: {', '.join(unauthorized)}]")
                continue

        sanitized_lines.append(line)

    if has_dropped_claim:
        sanitized_lines.append("\n> ⚠️ [ABSTENTION: One or more claims were dropped due to lack of verified citation grounding.]")

    return "\n".join(sanitized_lines)


def detect_prompt_injection(text: str) -> Tuple[bool, List[str]]:
    """
    Scans untrusted text extracted from uploaded PDFs for adversarial injection attempts.
    Returns (is_suspicious, matched_patterns).
    """
    if not text:
        return False, []

    matches: List[str] = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        found = pattern.findall(text)
        if found:
            # Flatten matched tuples or strings
            for f in found:
                match_str = f[0] if isinstance(f, tuple) else f
                if match_str and match_str not in matches:
                    matches.append(match_str)

    is_suspicious = len(matches) > 0
    return is_suspicious, matches


def sanitize_document_text(text: str) -> str:
    """
    Neutralizes potential prompt-injection triggers in document text before
    passing it into delimited prompt contexts.
    """
    if not text:
        return ""

    sanitized = text
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = pattern.sub(r"[DEFUSED_ADVERSARIAL_SPAN: \1]", sanitized)

    # Escape triple backticks to prevent markdown prompt breakout
    sanitized = sanitized.replace("```", "'''")
    return sanitized

