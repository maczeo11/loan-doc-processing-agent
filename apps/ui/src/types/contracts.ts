/**
 * Frontend TypeScript contracts for FinScan AI.
 * Strictly mirrors core/contracts/ and apps/api/routes schemas.
 */

// --- Evidence & Bounding Boxes (core/contracts/evidence.py) ---

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  page_width?: number | null;
  page_height?: number | null;
}

export interface EvidenceRef {
  document_id: string;
  document_type: string;
  page_number: number;
  quoted_span: string;
  bounding_box?: BoundingBox | null;
  extraction_method?: string;
  confidence?: number;
}

// --- Domain Facts (core/contracts/facts.py) ---

export interface MoneyFact {
  amount: number;
  currency: string;
  period: "monthly" | "annual" | "one_time";
  basis: "gross" | "net" | "deduction" | "balance";
  source: EvidenceRef;
}

export interface ApplicantFact {
  full_name: string;
  source_name: EvidenceRef;
  dob?: string | null;
  source_dob?: EvidenceRef | null;
  pan_number?: string | null;
  source_pan?: EvidenceRef | null;
  aadhaar_masked?: string | null;
  source_aadhaar?: EvidenceRef | null;
}

export interface PayslipFacts {
  employee_name: string;
  employer_name: string;
  gross_salary: MoneyFact;
  net_salary: MoneyFact;
  deductions_total?: MoneyFact | null;
  pay_period_str?: string | null;
}

export interface BankStatementFacts {
  account_holder: string;
  bank_name: string;
  account_number_masked: string;
  salary_credits: MoneyFact[];
  average_salary_credit?: MoneyFact | null;
  closing_balance?: MoneyFact | null;
  bounced_transactions: number;
}

export interface TaxReturnFacts {
  assessee_name: string;
  pan_number: string;
  assessment_year: string;
  gross_total_income: MoneyFact;
  total_tax_paid?: MoneyFact | null;
}

// --- Findings & Deterministic Rules (core/contracts/findings.py) ---

export type RuleVerdict = "pass" | "flag" | "unknown";

export interface Finding {
  rule_id: string;
  rule_name: string;
  verdict: RuleVerdict;
  reason: string;
  supporting_evidence: EvidenceRef[];
  policy_version: string;
}

// --- Application State & Lifecycle (core/contracts/state.py) ---

export type ApplicationStatus =
  | "UPLOADED"
  | "QUEUED"
  | "PROCESSING"
  | "READY_FOR_REVIEW"
  | "NEEDS_INFORMATION"
  | "REVIEWED"
  | "FAILED"
  | "CANCELLED";

export interface StatusTransition {
  from_status: ApplicationStatus;
  to_status: ApplicationStatus;
  timestamp: string;
  reason?: string | null;
}

export interface LoanApplicationState {
  application_id: string;
  status: ApplicationStatus;
  status_history?: StatusTransition[];

  // Raw document references
  document_ids?: string[];
  document_manifest?: Record<string, string>;
  classified_types?: Record<string, string>;

  // Extracted facts
  applicant?: ApplicantFact | null;
  payslip?: PayslipFacts | null;
  bank_statement?: BankStatementFacts | null;
  tax_return?: TaxReturnFacts | null;

  // Findings
  findings?: Finding[];
  missing_documents?: string[];

  // RAG policy citations & summary
  retrieved_chunk_ids?: string[];
  summary_markdown?: string | null;
  summary_grounded?: boolean;

  // Human-in-the-loop review
  review_paused?: boolean;
  reviewer_decision?: "APPROVED" | "REJECTED" | "NEEDS_INFO" | null;
  reviewer_notes?: string | null;
  corrections_applied?: Array<Record<string, unknown>>;
}

// --- API Request/Response Models (apps/api/routes/) ---

export interface CreateApplicationRequest {
  applicant_name: string;
  loan_amount: number;
  loan_purpose?: string | null;
}

export interface CreateApplicationResponse {
  application_id: string;
  status: string;
}

export interface ProcessApplicationResponse {
  job_id: string;
  application_id: string;
  status: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  application_id: string;
  filename: string;
  sha256: string;
  size_bytes: number;
}

export interface JobStatusResponse {
  job_id: string;
  application_id: string;
  status: string;
  attempt_count: number;
  error_message?: string | null;
}

export interface ReviewDecisionRequest {
  decision: "APPROVED" | "REJECTED" | "NEEDS_INFO";
  reviewer_id: string;
  notes?: string | null;
  corrections?: Array<Record<string, unknown>>;
}

export interface ReviewDecisionResponse {
  application_id: string;
  decision: string;
  status: string;
}

export interface Citation {
  document_id?: string;
  document_type?: string;
  page_number?: number;
  quoted_span?: string;
  bounding_box?: BoundingBox | null;
  extraction_method?: string;
  confidence?: number;
  chunk_id?: string;
  policy_id?: string;
  section?: string;
  title?: string;
  text?: string;
  [key: string]: unknown;
}

export interface QuestionRequest {
  question: string;
}

export interface QuestionResponse {
  answer: string;
  citations: Citation[];
}

export interface ExportResponse {
  application_id: string;
  export_format: string;
}
