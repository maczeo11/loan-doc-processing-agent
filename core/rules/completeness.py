"""
Completeness Rule (RULE-COMP-01): Verifies presence of all required documents in the dossier.
HUMAN-ONLY ZONE: Owned by Member 4 (Sravanthi).

Invariants:
  1. Deterministic Python logic — no LLM decides verdicts.
  2. Required documents for retail loan appraisal:
     - Application Form (1)
     - Salary Payslips (3 months)
     - Bank Statement (1)
     - Income Tax Return (ITR-V) (1)
     - Government-issued Identity / KYC Proof (1)
  3. Verdicts:
     - 'pass': All mandatory documents are present and usable.
     - 'flag': One or more required documents are missing.
     - 'unknown': Document presence or classification state cannot be determined.
  4. Returns typed Finding contract with evidence citations when available.
"""

from collections import Counter
from typing import Dict, List, Optional
from core.contracts.evidence import EvidenceRef
from core.contracts.findings import Finding

# Canonical document categories required for retail loan evaluation
CANONICAL_REQUIRED_DOCS = [
    "application_form",
    "payslip",
    "bank_statement",
    "tax_acknowledgement",
    "id_card",
]

DOC_TYPE_ALIASES: Dict[str, str] = {
    "application_form": "application_form",
    "application": "application_form",
    "loan_application": "application_form",
    "application.pdf": "application_form",
    "payslip": "payslip",
    "payslips": "payslip",
    "salary_slip": "payslip",
    "salary_payslip": "payslip",
    "payslip_1.pdf": "payslip",
    "payslip_2.pdf": "payslip",
    "payslip_3.pdf": "payslip",
    "bank_statement": "bank_statement",
    "bank_stmt": "bank_statement",
    "bank_statement.pdf": "bank_statement",
    "tax_acknowledgement": "tax_acknowledgement",
    "itr": "tax_acknowledgement",
    "itr_v": "tax_acknowledgement",
    "itr.pdf": "tax_acknowledgement",
    "tax_return": "tax_acknowledgement",
    "id_card": "id_card",
    "kyc": "id_card",
    "kyc_id": "id_card",
    "kyc.pdf": "id_card",
    "pan_card": "id_card",
    "aadhaar": "id_card",
}

DOC_TYPE_DISPLAY_NAMES: Dict[str, str] = {
    "application_form": "Application Form",
    "payslip": "Salary Payslip",
    "bank_statement": "Bank Statement",
    "tax_acknowledgement": "ITR",
    "id_card": "KYC ID",
}

UNKNOWN_INDICATORS = {
    "unknown",
    "unclassified",
    "unreadable",
    "corrupted",
    "unusable",
    "error",
}


def normalize_doc_type(raw_type: Optional[str]) -> Optional[str]:
    """Normalizes document types and filenames to canonical category names."""
    if raw_type is None:
        return None
    cleaned = str(raw_type).strip().lower()
    return DOC_TYPE_ALIASES.get(cleaned, cleaned)


def evaluate_completeness(
    uploaded_types: Optional[List[str]] = None,
    required_types: Optional[List[str]] = None,
    evidence: Optional[List[EvidenceRef]] = None,
    min_payslips: Optional[int] = None,
    is_available: bool = True,
) -> Finding:
    """
    Evaluates RULE-COMP-01: Verifies presence and usability of all mandatory dossier documents.

    Parameters:
      uploaded_types: List of classified document types or filenames uploaded for the application.
      required_types: Optional explicit list of required types. If omitted, defaults to standard
                      retail loan dossier requirements: application_form (1), payslip (3),
                      bank_statement (1), tax_acknowledgement (1), id_card (1).
      evidence: Optional list of EvidenceRefs grounding the uploaded documents.
      min_payslips: Optional override for required payslip count. If provided, overrides
                    the payslip count from required_types.
      is_available: Boolean flag indicating if document classification state is available.

    Returns:
      Finding with rule_id='RULE-COMP-01', rule_name='Dossier Completeness Check',
      verdict ('pass' | 'flag' | 'unknown'), explanation, and supporting evidence.
    """
    # 1. Guard against unavailable or unknown document state
    if not is_available or uploaded_types is None:
        return Finding(
            rule_id="RULE-COMP-01",
            rule_name="Dossier Completeness Check",
            verdict="unknown",
            reason="Document availability or classification status cannot be determined (unavailable state).",
            supporting_evidence=[],
            policy_version="v1.0",
        )

    # Check for any unreadable / unknown / corrupted document indicators
    for item in uploaded_types:
        if item is None or str(item).strip().lower() in UNKNOWN_INDICATORS:
            return Finding(
                rule_id="RULE-COMP-01",
                rule_name="Dossier Completeness Check",
                verdict="unknown",
                reason=f"Document classification state is unknown or unreadable (contains '{item}').",
                supporting_evidence=[],
                policy_version="v1.0",
            )

    # 2. Normalize uploaded document types
    normalized_uploaded = [normalize_doc_type(t) for t in uploaded_types if t is not None]
    uploaded_counts = Counter(normalized_uploaded)

    # 3. Determine required counts
    if required_types is not None:
        normalized_required = [normalize_doc_type(t) for t in required_types if t is not None]
        required_counts = Counter(normalized_required)
    else:
        # Default retail loan dossier requirements per AGENTS.md
        required_counts = {
            "application_form": 1,
            "payslip": 3,
            "bank_statement": 1,
            "tax_acknowledgement": 1,
            "id_card": 1,
        }

    # Apply explicit min_payslips override if requested
    if min_payslips is not None:
        required_counts["payslip"] = max(0, min_payslips)

    # 4. Check for missing documents
    missing_descriptions: List[str] = []
    for doc_type, needed_count in required_counts.items():
        present_count = uploaded_counts.get(doc_type, 0)
        if present_count < needed_count:
            display_name = DOC_TYPE_DISPLAY_NAMES.get(doc_type, doc_type)
            if needed_count > 1:
                missing_descriptions.append(
                    f"{doc_type} ({display_name}: found {present_count} of {needed_count} required)"
                )
            else:
                missing_descriptions.append(f"{doc_type} ({display_name})")

    # 5. Filter matching evidence if supplied
    supporting_evidence: List[EvidenceRef] = []
    if evidence:
        for ev in evidence:
            ev_type = normalize_doc_type(getattr(ev, "document_type", None))
            if ev_type in uploaded_counts:
                supporting_evidence.append(ev)

    # 6. Formulate verdict and finding
    if not missing_descriptions:
        payslip_count = required_counts.get("payslip", 1)
        payslip_str = f"{payslip_count} Payslips" if payslip_count > 1 else "Payslip"
        return Finding(
            rule_id="RULE-COMP-01",
            rule_name="Dossier Completeness Check",
            verdict="pass",
            reason=f"All required documents are present and verified (Application Form, {payslip_str}, Bank Statement, ITR, KYC ID).",
            supporting_evidence=supporting_evidence,
            policy_version="v1.0",
        )

    return Finding(
        rule_id="RULE-COMP-01",
        rule_name="Dossier Completeness Check",
        verdict="flag",
        reason=f"Missing mandatory documents: {', '.join(missing_descriptions)}",
        supporting_evidence=supporting_evidence,
        policy_version="v1.0",
    )
