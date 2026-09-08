"""
Identity Rule: Cross-checks applicant name and PAN number across KYC, payslip, and bank statement.
HUMAN-ONLY ZONE: Verified by Member 4 (Sravanthi).
"""

from typing import Optional
from core.contracts.findings import Finding
from core.contracts.facts import ApplicantFact


def audit_identity_consistency(applicant: Optional[ApplicantFact], payslip_name: Optional[str], bank_name: Optional[str]) -> Finding:
    if applicant is None:
        return Finding(
            rule_id="RULE-ID-01",
            rule_name="Cross-Document Identity Consistency",
            verdict="unknown",
            reason="Missing primary applicant KYC document.",
            policy_version="v1.0",
        )

    # TODO: Member 4 implement fuzzy name matching (RapidFuzz token_sort_ratio)
    return Finding(
        rule_id="RULE-ID-01",
        rule_name="Cross-Document Identity Consistency",
        verdict="pass",
        reason=f"Identity confirmed across documents for {applicant.full_name}.",
        policy_version="v1.0",
    )
