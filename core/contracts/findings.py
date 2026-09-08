"""
Findings: The output of deterministic verification rules in core/rules/.
No verdict originates from an LLM. Rules compute them; LLMs only narrate them.
"""

from typing import List, Literal
from pydantic import BaseModel, Field
from core.contracts.evidence import EvidenceRef

RuleVerdict = Literal["pass", "flag", "unknown"]


class Finding(BaseModel):
    rule_id: str = Field(..., description="Unique rule identifier e.g. RULE-INC-01")
    rule_name: str = Field(..., description="Human-readable rule title")
    verdict: RuleVerdict = Field(..., description="'pass' | 'flag' | 'unknown'")
    reason: str = Field(..., description="Clear explanation of the determination")
    supporting_evidence: List[EvidenceRef] = Field(default_factory=list, description="All citations grounding this finding")
    policy_version: str = Field("v1.0", description="Version of credit policy rule evaluated against")
