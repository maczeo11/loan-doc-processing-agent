import type { BoundingBox } from './evidence';

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
  // Present only when the citation points at an uploaded document rather than
  // a policy-corpus chunk; enables jump-to-evidence on the PDF canvas.
  document_id?: string;
  document_type?: string;
  page_number?: number;
  bounding_box?: BoundingBox | null;
}

export interface PolicyQaResponse {
  question: string;
  answer: string;
  citations: PolicyCitation[];
  is_grounded: boolean;
}
