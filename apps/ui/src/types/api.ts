import type { BoundingBox, ReviewDecisionRequest, ReviewDecisionResponse } from './contracts';

export type ReviewDecision = 'APPROVED' | 'REJECTED' | 'NEEDS_INFO';

export type { ReviewDecisionRequest, ReviewDecisionResponse };

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
