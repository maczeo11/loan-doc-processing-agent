/**
 * Re-exports canonical contract models from contracts.ts (Single Source of Truth)
 * and defines UI-specific navigation targets.
 */
export type { BoundingBox, EvidenceRef, RuleVerdict, Finding } from './contracts';
import type { BoundingBox } from './contracts';

export interface CitationNavigationTarget {
  documentId: string;
  pageNumber: number;
  evidenceId: string;
  boundingBox: BoundingBox;
}
