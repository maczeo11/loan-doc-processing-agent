import type { EvidenceRef, Finding, ApplicationStatus, ClassificationMetadata } from './contracts';

export type { ApplicationStatus, ClassificationMetadata };

export interface MoneyFact {
  amount: number;
  currency: string;
  period?: string | null;
  gross_or_net?: string | null;
  basis?: string | null;
  source: EvidenceRef;
}

export interface ApplicantFact {
  full_name?: string | null;
  source_name?: EvidenceRef | null;
  pan_number?: string | null;
  source_pan?: EvidenceRef | null;
}

export interface PayslipFacts {
  employee_name?: string | null;
  employer_name?: string | null;
  gross_salary?: MoneyFact | null;
  net_salary?: MoneyFact | null;
  pay_period?: string | null;
  pay_period_str?: string | null;
  deductions_total?: MoneyFact | null;
}

export interface BankStatementFacts {
  account_holder?: string | null;
  bank_name?: string | null;
  account_number_masked?: string | null;
  salary_credits: MoneyFact[];
  average_salary_credit?: MoneyFact | null;
  closing_balance?: MoneyFact | null;
  bounced_transactions: number;
}

export interface TaxReturnFacts {
  assessee_name?: string | null;
  pan_number?: string | null;
  assessment_year?: string | null;
  gross_total_income?: MoneyFact | null;
  total_tax_paid?: MoneyFact | null;
}

export type OcrRoute = 'native' | 'ocr' | 'paddle' | 'textract';

export interface DossierDocument {
  id: string;
  name: string;
  document_type: string;
  /** Real page count from perception; undefined until it is actually known. */
  page_count?: number;
  /** Route that produced the text layer; undefined until perception has run. */
  ocr_route?: OcrRoute;
  /** ML classification metadata (confidence, alternative class probabilities, triage flags). */
  classification?: ClassificationMetadata;
  /** True only when a finding cites this document as supporting evidence. */
  verified: boolean;
}

export interface LoanApplication {
  id: string;
  applicant_name: string;
  pan_masked: string;
  /** Undefined when the backend has not supplied an amount — never defaulted. */
  loan_amount?: number;
  currency: string;
  status: ApplicationStatus;
  /** Undefined until a status transition establishes the clock start. */
  created_at?: string;
  updated_at?: string;
  documents: DossierDocument[];
  findings: Finding[];
  missing_documents?: string[];
  summary_grounded?: boolean;
  payslip_facts?: PayslipFacts;
  bank_facts?: BankStatementFacts;
  tax_facts?: TaxReturnFacts;
  applicant_facts?: ApplicantFact;
  memo_markdown?: string;
  reviewer_decision?: string | null;
  reviewer_notes?: string | null;
}
