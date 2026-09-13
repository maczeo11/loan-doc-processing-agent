"""
State: The authoritative LangGraph State contract and lifecycle definitions.
"""

from typing import TypedDict, List, Dict, Optional, Literal, Any
from core.contracts.facts import ApplicantFact, PayslipFacts, BankStatementFacts, TaxReturnFacts
from core.contracts.findings import Finding

ApplicationStatus = Literal[
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "READY_FOR_REVIEW",
    "NEEDS_INFORMATION",
    "REVIEWED",
    "FAILED",
    "CANCELLED"
]


class StatusTransition(TypedDict):
    from_status: ApplicationStatus
    to_status: ApplicationStatus
    timestamp: str
    reason: Optional[str]


class ClassificationMetadata(TypedDict, total=False):
    confidence: float
    class_probabilities: Dict[str, float]
    model_version: str
    method: Literal["ml_baseline", "heuristic_fallback", "user_override"]
    requires_human_triage: bool


class LoanApplicationState(TypedDict):
    """
    Authoritative state dictionary passed through LangGraph nodes.
    """
    application_id: str
    status: ApplicationStatus
    status_history: List[StatusTransition]

    # Raw document references in storage
    document_ids: List[str]
    document_manifest: Dict[str, str]  # doc_id -> storage_uri
    document_bytes: Optional[Dict[str, bytes]]
    classified_types: Dict[str, str]  # doc_id -> doc_type
    # ML classification metadata (confidence, class distribution, triage status)
    classification_metadata: Optional[Dict[str, ClassificationMetadata]]
    # Observed during perception, not guessed by the UI: real page count and the
    # route that actually produced the text layer for each document.
    document_pages: Dict[str, int]  # doc_id -> page count
    ocr_routes: Dict[str, str]  # doc_id -> 'native' | 'ocr'
    # Per-page OCR/router output cached by Node 2 (ocr_and_classify_node) so Node 3
    # (extract_facts_node) reuses it instead of re-running a full OCR pass. Must be
    # declared here to survive the compiled LangGraph's state-channel merge - a key
    # a node returns but that isn't part of this TypedDict is silently dropped between
    # nodes. Each value is a list of page dicts: {"page_number", "text", "page_width",
    # "page_height"} (older cached str-list values are still read for back-compat).
    document_texts: Optional[Dict[str, Any]]

    # Extracted structured facts
    applicant: Optional[ApplicantFact]
    payslip: Optional[PayslipFacts]
    bank_statement: Optional[BankStatementFacts]
    tax_return: Optional[TaxReturnFacts]
    # Every uploaded identity-type document (id_card/kyc/pan/aadhaar), not just
    # the first one. `applicant` above stays the first-extracted doc for
    # backward compatibility with existing consumers (memo, UI); this list is
    # what lets RULE-ID-02 (core/rules/identity.py) cross-check name/PAN
    # between e.g. a separately uploaded ID card AND PAN card. Each item:
    # {"doc_id": str, "fact": ApplicantFact}.
    identity_documents: List[Dict[str, Any]]

    # Deterministic rule findings
    findings: List[Finding]
    missing_documents: List[str]

    # RAG policy citations & AI summary
    retrieved_chunk_ids: List[str]
    summary_markdown: Optional[str]
    summary_grounded: bool

    # Human-in-the-loop review
    review_paused: bool
    reviewer_decision: Optional[Literal["APPROVED", "REJECTED", "NEEDS_INFO"]]
    reviewer_notes: Optional[str]
    corrections_applied: List[Dict[str, Any]]
