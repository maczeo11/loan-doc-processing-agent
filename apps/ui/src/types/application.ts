import { EvidenceRef, Finding } from './evidence';

export type ApplicationStatus =
  | 'UPLOADED'
  | 'QUEUED'
  | 'PROCESSING'
  | 'READY_FOR_REVIEW'
  | 'NEEDS_INFORMATION'
  | 'REVIEWED'
  | 'FAILED'
  | 'CANCELLED';

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

export interface DossierDocument {
  id: string;
  name: string;
  document_type: string;
  // Below are populated only when the backend provides them.
  // Never synthesize: no fake page counts, OCR routes, or verified ticks.
  page_count?: number;
  ocr_route?: 'native' | 'paddle' | 'textract';
  verified?: boolean;
  signed_url?: string;
  download_url?: string;
}

export interface LoanApplication {
  id: string;
  applicant_name: string;
  pan_masked: string;
  loan_amount: number;
  currency: string;
  status: ApplicationStatus;
  created_at: string;
  updated_at?: string;
  documents: DossierDocument[];
  findings: Finding[];
  payslip_facts?: PayslipFacts;
  bank_facts?: BankStatementFacts;
  tax_facts?: TaxReturnFacts;
  applicant_facts?: ApplicantFact;
  memo_markdown?: string;
  reviewer_decision?: string | null;
  reviewer_notes?: string | null;
}
