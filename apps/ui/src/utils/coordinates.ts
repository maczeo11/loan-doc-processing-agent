import { BoundingBox, EvidenceRef } from '../types/evidence';

export interface BoundingBoxPercent {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * Converts a backend BoundingBox (either normalized 0..1 or PDF points)
 * into responsive CSS percentages (0..100) relative to the rendered page.
 */
export function computeBoundingBoxPercent(bbox: BoundingBox): BoundingBoxPercent {
  const isNormalized =
    bbox.x1 <= 1.05 &&
    bbox.y1 <= 1.05 &&
    (!bbox.page_width || bbox.page_width <= 1.05);

  let left: number;
  let top: number;
  let width: number;
  let height: number;

  if (isNormalized) {
    left = bbox.x0 * 100;
    top = bbox.y0 * 100;
    width = (bbox.x1 - bbox.x0) * 100;
    height = (bbox.y1 - bbox.y0) * 100;
  } else {
    const pageW = bbox.page_width && bbox.page_width > 0 ? bbox.page_width : 595.28;
    const pageH = bbox.page_height && bbox.page_height > 0 ? bbox.page_height : 841.89;

    left = (bbox.x0 / pageW) * 100;
    top = (bbox.y0 / pageH) * 100;
    width = ((bbox.x1 - bbox.x0) / pageW) * 100;
    height = ((bbox.y1 - bbox.y0) / pageH) * 100;
  }

  // Safety clamping & minimum visibility
  const clampedLeft = Math.max(0, Math.min(99, left));
  const clampedTop = Math.max(0, Math.min(99, top));
  const clampedWidth = Math.max(1.0, Math.min(100 - clampedLeft, Math.abs(width)));
  const clampedHeight = Math.max(0.8, Math.min(100 - clampedTop, Math.abs(height)));

  return {
    left: clampedLeft,
    top: clampedTop,
    width: clampedWidth,
    height: clampedHeight,
  };
}

/**
 * Creates a unique stable key identifying an evidence citation.
 */
export function getEvidenceKey(evidence: EvidenceRef): string {
  const b = evidence.bounding_box;
  return `${evidence.document_id}-P${evidence.page_number}-${b.x0.toFixed(2)}_${b.y0.toFixed(2)}`;
}
