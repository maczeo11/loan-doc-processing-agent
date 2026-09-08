"""
Completeness Rule: Verifies presence of all required documents in the dossier.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

from typing import List
from core.contracts.findings import Finding


def evaluate_completeness(uploaded_types: List[str], required_types: List[str]) -> Finding:
    """
    Checks if application form, payslip, bank statement, tax return, and ID proof are present.
    """
    missing = [doc for doc in required_types if doc not in uploaded_types]
    if not missing:
        return Finding(
            rule_id="RULE-COMP-01",
            rule_name="Dossier Completeness Check",
            verdict="pass",
            reason="All required documents are present.",
            policy_version="v1.0",
        )
    return Finding(
        rule_id="RULE-COMP-01",
        rule_name="Dossier Completeness Check",
        verdict="flag",
        reason=f"Missing mandatory documents: {', '.join(missing)}",
        policy_version="v1.0",
    )
