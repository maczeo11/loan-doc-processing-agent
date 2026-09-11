"""
Grounding Validation & Prompt-Injection Defense.
HUMAN-ONLY ZONE: Validated by Member 8 (Sai Mokshith).

Invariants & Guarantees from AGENTS.md:
- Deterministic citation validation: every claim in CAM must cite authorized chunk IDs.
- Zero Hallucinated Decisions: unsupported claims are dropped; summary abstains if evidence missing.
- Prompt Injection Defense: untrusted document text is sanitized against adversarial override attempts.
- LLM Narrative Firewall: text from LLMPort.generate_summary must reproduce only
  pre-computed finding numbers, cite only authorized chunks, and never issue a
  lending disposition (approve/reject). Violations fail closed.
"""

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Set, Tuple

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
    known_doc_ids: Optional[Set[str]] = None,
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
    doc_set = {d.upper() for d in (known_doc_ids or set())}
    lines = summary_text.splitlines()
    sanitized_lines: List[str] = []
    has_dropped_claim = False

    for line in lines:
        # Search for citation tags like [DOC_p1] or [credit_policy_v1_p1]
        citation_matches = re.findall(r"\[([a-zA-Z0-9_\-]+)\]", line)
        if citation_matches:
            unauthorized = [
                c for c in citation_matches
                if c not in authorized_set
                and not c.upper().startswith(("PASS", "FLAG", "UNKNOWN", "ABSTENTION", "DOC", "APP"))
                and c.upper() not in doc_set
            ]
            if unauthorized:
                has_dropped_claim = True
                sanitized_lines.append(f"> ⚠️ [UNGROUNDED CLAIM DROPPED - Unauthorized citations: {', '.join(unauthorized)}]")
                continue

        sanitized_lines.append(line)

    if has_dropped_claim:
        sanitized_lines.append("\n> ⚠️ [ABSTENTION: One or more claims were dropped due to lack of verified citation grounding.]")

    return "\n".join(sanitized_lines)


# Autonomous disposition language an LLM narrator must never emit.
# (Findings use pass/flag/unknown; approve/reject belongs to the human reviewer.)
DISPOSITION_PATTERNS = [
    re.compile(r"\b(approve[sd]?|approving|approval\s+(granted|is\s+therefore))\b", re.IGNORECASE),
    re.compile(r"\b(reject[sed]?|rejecting|rejection)\b", re.IGNORECASE),
    re.compile(r"\b(sanction[sed]?|sanctioning)\b", re.IGNORECASE),
    re.compile(r"\b(loan\s+(is\s+)?(approved|rejected|sanctioned|denied|declined|granted))\b", re.IGNORECASE),
    re.compile(r"\b(credit\s+decision\s+is\s+(favourable|favorable|positive|negative))\b", re.IGNORECASE),
]

# Monetary figures: optional INR/₹/Rs prefix, grouped digits, optional decimals.
MONEY_PATTERN = re.compile(
    r"(?:₹|INR|Rs\.?)?\s*(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+\.\d{1,2})"
)

# Verdict-badge tokens the deterministic memo legitimately emits.
LEGIT_BADGE_PREFIXES = ("PASS", "FLAG", "UNKNOWN", "ABSTENTION")


def _normalize_money(raw: str) -> Optional[Decimal]:
    """Normalizes a matched money string to Decimal for exact comparison."""
    try:
        return Decimal(raw.replace(",", ""))
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _money_in_text(text: str) -> Set[Decimal]:
    """Extracts the set of monetary figures appearing in free text."""
    found: Set[Decimal] = set()
    for match in MONEY_PATTERN.finditer(text or ""):
        amount = _normalize_money(match.group(1))
        if amount is not None:
            found.add(amount)
    return found


def _finding_numbers(findings: List[Any]) -> Set[Decimal]:
    """Collects every monetary figure from deterministic finding reasons."""
    numbers: Set[Decimal] = set()
    for finding in findings:
        reason = ""
        if isinstance(finding, dict):
            reason = str(finding.get("reason", ""))
        else:
            reason = str(getattr(finding, "reason", ""))
        numbers |= _money_in_text(reason)
    return numbers


def validate_llm_narrative(
    narrative: str,
    findings: List[Any],
    authorized_chunk_ids: List[str],
) -> Dict[str, Any]:
    """
    Firewalls LLM-generated memo narration (LLMPort.generate_summary output).

    The LLM may phrase and explain, but deterministically verified constraints hold:
      1. No autonomous disposition language (approve/reject/sanction...).
      2. Every monetary figure must already appear in the deterministic findings.
      3. Every [bracket citation] must be an authorized chunk ID (badge tokens exempt).
      4. No prompt-injection patterns may be present.

    Returns {"grounded": bool, "issues": [str, ...]}. Fails closed: empty
    narrative, missing findings, or any violation grounds=False.
    """
    issues: List[str] = []

    if not narrative or not narrative.strip():
        return {"grounded": False, "issues": ["empty narrative: nothing to verify"]}

    if not findings:
        issues.append("no deterministic findings supplied: narrative has no numeric anchor")

    for pattern in DISPOSITION_PATTERNS:
        match = pattern.search(narrative)
        if match:
            issues.append(
                f"autonomous disposition language forbidden: '{match.group(0).strip()}'"
            )

    allowed_numbers = _finding_numbers(findings or [])
    for amount in sorted(_money_in_text(narrative)):
        if amount not in allowed_numbers:
            issues.append(f"ungrounded monetary figure not in findings: {amount:,.2f}")

    authorized_set = _expand_authorized_ids(authorized_chunk_ids or [])
    for citation in re.findall(r"\[([a-zA-Z0-9_\-]+)\]", narrative):
        if citation.upper().startswith(LEGIT_BADGE_PREFIXES):
            continue
        if citation not in authorized_set:
            issues.append(f"unauthorized citation in narrative: [{citation}]")

    injected, matches = detect_prompt_injection(narrative)
    if injected:
        issues.append(f"prompt-injection pattern in narrative: {matches[0]}")

    if issues:
        logger.warning(f"LLM narrative failed grounding: {issues[0]}")
    return {"grounded": not issues, "issues": issues}


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

