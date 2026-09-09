"""
FinScan AI: Deterministic Rules Engine.
HUMAN-ONLY ZONE: Owned by Member 4 (Sravanthi).
Deterministic code decides. AI explains. A human approves.
"""

from core.rules.completeness import evaluate_completeness
from core.rules.salary_audit import audit_salary_vs_bank
from core.rules.tax_audit import audit_tax_vs_income
from core.rules.identity import audit_identity_consistency, compute_name_similarity, normalize_name_tokens

__all__ = [
    "evaluate_completeness",
    "audit_salary_vs_bank",
    "audit_tax_vs_income",
    "audit_identity_consistency",
    "compute_name_similarity",
    "normalize_name_tokens",
]
