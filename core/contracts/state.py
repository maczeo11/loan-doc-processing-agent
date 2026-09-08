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

    # Extracted structured facts
    applicant: Optional[ApplicantFact]
    payslip: Optional[PayslipFacts]
    bank_statement: Optional[BankStatementFacts]
    tax_return: Optional[TaxReturnFacts]

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
