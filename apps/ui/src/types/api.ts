export type ReviewDecision = 'APPROVED' | 'REJECTED' | 'NEEDS_INFO';

export interface ReviewDecisionRequest {
  decision: ReviewDecision;
  reviewer_id: string;
  notes?: string;
  corrections?: Array<Record<string, unknown>>;
}

export interface ReviewDecisionResponse {
  application_id: string;
  status: string;
  updated_at: string;
  decision?: string;
}

export interface PolicyCitation {
  chunk_id: string;
  policy_name: string;
  section: string;
  text: string;
  score: number;
}

export interface PolicyQaResponse {
  question: string;
  answer: string;
  citations: PolicyCitation[];
  is_grounded: boolean;
}
