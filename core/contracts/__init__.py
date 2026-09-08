"""
Core Contracts: The shared source of truth for FinScan AI.
"""

from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import (
    MoneyFact,
    ApplicantFact,
    PayslipFacts,
    BankStatementFacts,
    TaxReturnFacts,
)
from core.contracts.findings import Finding, RuleVerdict
from core.contracts.state import LoanApplicationState, ApplicationStatus
from core.contracts.jobs import JobRef

__all__ = [
    "EvidenceRef",
    "BoundingBox",
    "MoneyFact",
    "ApplicantFact",
    "PayslipFacts",
    "BankStatementFacts",
    "TaxReturnFacts",
    "Finding",
    "RuleVerdict",
    "LoanApplicationState",
    "ApplicationStatus",
    "JobRef",
]
