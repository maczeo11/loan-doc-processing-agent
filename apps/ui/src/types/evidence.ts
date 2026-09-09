export interface BoundingBox {
  x0: number; // PDF points or normalized 0..1
  y0: number;
  x1: number;
  y1: number;
  page_width?: number;
  page_height?: number;
}

export interface EvidenceRef {
  document_id: string;
  document_type: string;
  page_number: number; // 1-indexed
  quoted_span: string;
  bounding_box: BoundingBox;
}

export type RuleVerdict = 'pass' | 'flag' | 'unknown';

export interface Finding {
  rule_id: string;
  rule_name: string;
  verdict: RuleVerdict;
  reason: string;
  supporting_evidence: EvidenceRef[];
  policy_version: string;
}

export interface CitationNavigationTarget {
  documentId: string;
  pageNumber: number;
  evidenceId: string;
  boundingBox: BoundingBox;
}
