"""
FinScan AI: Core Pydantic Schemas and LangGraph State Contract
This file acts as the single source of truth for the entire 8-person team.
"""

from typing import TypedDict, List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field


class ExtractedApplicant(BaseModel):
    full_name: str = Field(..., description="Full legal name of the applicant")
    dob: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format")
    pan_number: Optional[str] = Field(None, description="10-character PAN card number")
    aadhaar_masked: Optional[str] = Field(None, description="Masked Aadhaar number (e.g. XXXX-XXXX-1234)")
    current_address: Optional[str] = Field(None, description="Residential address extracted from KYC")


class ExtractedPayslip(BaseModel):
    employee_name: str
    employer_name: str
    pay_period: Optional[str] = None
    gross_salary: float = Field(..., description="Monthly gross salary before deductions")
    net_salary: float = Field(..., description="Monthly net take-home salary credited")
    provident_fund: Optional[float] = 0.0
    tax_deducted: Optional[float] = 0.0


class ExtractedBankStatement(BaseModel):
    account_holder: str
    bank_name: str
    account_number_masked: str
    average_monthly_balance: float
    detected_monthly_salary_credits: List[float] = Field(default_factory=list)
    average_monthly_salary_credit: float
    total_debits_3m: float
    total_credits_3m: float
    bounced_transactions_count: int = Field(0, description="Count of cheque/ECS bounce charges")


class ExtractedTaxReturn(BaseModel):
    assessee_name: str
    pan_number: str
    assessment_year: str
    gross_total_income: float
    total_tax_paid: float


class Discrepancy(BaseModel):
    category: Literal[
        "IDENTITY_MISMATCH",
        "INCOME_INFLATION",
        "MISSING_DOC",
        "MATH_INCONSISTENCY",
        "TAX_DISCREPANCY",
        "HIGH_RISK_FINANCIALS"
    ]
    severity: Literal["CRITICAL", "WARNING", "INFO"]
    title: str
    description: str
    source_documents: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class TabularModelPrediction(BaseModel):
    approval_probability: float = Field(..., ge=0.0, le=1.0)
    risk_tier: Literal["LOW", "MODERATE", "HIGH"]
    recommendation: Literal["APPROVE", "FLAG_FOR_REVIEW", "REJECT"]
    top_positive_features: List[Dict[str, Any]] = Field(default_factory=list)
    top_risk_features: List[Dict[str, Any]] = Field(default_factory=list)


class LoanApplicationState(TypedDict):
    """
    Shared State Dictionary passed across all nodes in the LangGraph StateGraph.
    """
    application_id: str
    raw_files: Dict[str, str]  # e.g. {"payslip": "path/or/s3_url", "bank_statement": "..."}
    uploaded_doc_types: List[str]  # e.g. ["payslip", "bank_statement", "kyc_pan"]
    missing_docs: List[str]  # e.g. ["tax_return"]

    # Extracted structured schemas
    applicant_data: Optional[ExtractedApplicant]
    payslip_data: Optional[ExtractedPayslip]
    bank_data: Optional[ExtractedBankStatement]
    tax_data: Optional[ExtractedTaxReturn]

    # Reconciliation and fraud analysis
    discrepancies: List[Discrepancy]
    fraud_risk_score: float  # 0.0 to 1.0 (higher is riskier)

    # Kaggle Tabular Model evaluation
    tabular_features: Dict[str, Any]
    ml_prediction: Optional[TabularModelPrediction]

    # Executive memo & Human-in-the-loop review
    credit_memo_markdown: str
    human_review_required: bool
    underwriter_decision: Optional[Literal["APPROVED", "REJECTED", "NEED_MORE_INFO"]]
    underwriter_notes: Optional[str]
    audit_trail: List[str]
