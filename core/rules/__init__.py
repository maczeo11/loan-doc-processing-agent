"""
FinScan AI: Deterministic Rules Engine.
HUMAN-ONLY ZONE: Owned by Member 4 (Sravanthi).
Deterministic code decides. AI explains. A human approves.
"""

from core.rules.completeness import evaluate_completeness, normalize_doc_type
from core.rules.salary_audit import audit_salary_vs_bank
from core.rules.tax_audit import audit_tax_vs_income
from core.rules.identity import audit_identity_consistency, compute_name_similarity, normalize_name_tokens, normalize_pan
from core.rules.bank_arithmetic import (
    validate_bank_statement_arithmetic,
    audit_bank_statement_arithmetic,
    audit_bank_arithmetic,
)
from core.rules.engine import evaluate_dossier_rules, findings_to_dict

__all__ = [
    "evaluate_completeness",
    "normalize_doc_type",
    "audit_salary_vs_bank",
    "audit_tax_vs_income",
    "audit_identity_consistency",
    "compute_name_similarity",
    "normalize_name_tokens",
    "normalize_pan",
    "validate_bank_statement_arithmetic",
    "audit_bank_statement_arithmetic",
    "audit_bank_arithmetic",
    "evaluate_dossier_rules",
    "findings_to_dict",
]
