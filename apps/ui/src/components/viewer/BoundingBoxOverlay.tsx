import React from 'react';
import type { EvidenceRef, BoundingBox } from '../../types/contracts';
import { EvidenceBox } from './EvidenceBox';
import { AlertCircle } from 'lucide-react';

interface PixelBounds {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface BoundingBoxOverlayProps {
  activeEvidence: EvidenceRef | null;
  activeRuleId?: string | null;
  canvasWidth: number;
  canvasHeight: number;
  unscaledPdfWidth?: number;
  unscaledPdfHeight?: number;
  currentDocId: string;
  currentPage: number;
}

function computePixelBounds(
  box: BoundingBox,
  renderedWidth: number,
  renderedHeight: number,
  unscaledWidth?: number,
  unscaledHeight?: number
): PixelBounds | null {
  if (
    box.x0 === undefined ||
    box.y0 === undefined ||
    box.x1 === undefined ||
    box.y1 === undefined
  ) {
    return null;
  }

  // Defensive check: If all coordinates are within ~[0, 1.05], treat as normalized coordinates
  const isNormalized =
    box.x0 <= 1.05 && box.y0 <= 1.05 && box.x1 <= 1.05 && box.y1 <= 1.05;

  let left: number;
  let top: number;
  let width: number;
  let height: number;

  if (isNormalized) {
    left = Math.round(box.x0 * renderedWidth);
    top = Math.round(box.y0 * renderedHeight);
    width = Math.round((box.x1 - box.x0) * renderedWidth);
    height = Math.round((box.y1 - box.y0) * renderedHeight);
  } else {
    // PDF points: scale using page_width/page_height if available, otherwise unscaledWidth/unscaledHeight or default 595 x 842 pt
    const pageWidth = box.page_width || unscaledWidth || 595;
    const pageHeight = box.page_height || unscaledHeight || 842;
    left = Math.round((box.x0 / pageWidth) * renderedWidth);
    top = Math.round((box.y0 / pageHeight) * renderedHeight);
    width = Math.round(((box.x1 - box.x0) / pageWidth) * renderedWidth);
    height = Math.round(((box.y1 - box.y0) / pageHeight) * renderedHeight);
  }

  // Bounded within canvas dimensions
  width = Math.max(14, width);
  height = Math.max(10, height);
  left = Math.max(0, Math.min(left, Math.max(0, renderedWidth - width)));
  top = Math.max(0, Math.min(top, Math.max(0, renderedHeight - height)));

  return { left, top, width, height };
}

export const BoundingBoxOverlay: React.FC<BoundingBoxOverlayProps> = ({
  activeEvidence,
  activeRuleId,
  canvasWidth,
  canvasHeight,
  unscaledPdfWidth,
  unscaledPdfHeight,
  currentDocId,
  currentPage,
}) => {
  // Clear/hide stale evidence if document or page does not match
  if (!activeEvidence) return null;
  const docMatches =
    activeEvidence.document_id?.toLowerCase() === currentDocId?.toLowerCase();
  if (
    !docMatches ||
    activeEvidence.page_number !== currentPage
  ) {
    return null;
  }

  // Case: Evidence cited without bounding box coordinates
  if (!activeEvidence.bounding_box) {
    return (
      <div className="absolute top-2 left-2 z-30 pointer-events-auto">
        <div className="bg-theme-card text-theme-unknown text-[11px] px-3 py-1.5 rounded-xs border border-theme-unknown-border shadow-lg flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Evidence cited on Page {currentPage} — Precise coordinates unavailable</span>
        </div>
      </div>
    );
  }

  const bounds = computePixelBounds(
    activeEvidence.bounding_box,
    canvasWidth,
    canvasHeight,
    unscaledPdfWidth,
    unscaledPdfHeight
  );
  if (!bounds) return null;

  return (
    <div
      style={{ width: `${canvasWidth}px`, height: `${canvasHeight}px` }}
      className="absolute inset-0 pointer-events-none overflow-hidden"
    >
      <EvidenceBox evidence={activeEvidence} bounds={bounds} isSelected={true} tag={activeRuleId} />
    </div>
  );
};
