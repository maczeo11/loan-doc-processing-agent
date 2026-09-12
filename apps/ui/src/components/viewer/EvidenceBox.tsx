import React from 'react';
import type { EvidenceRef } from '../../types/contracts';

interface PixelBounds {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface EvidenceBoxProps {
  evidence: EvidenceRef;
  bounds: PixelBounds;
  isSelected?: boolean;
  tag?: string | null;
}

/**
 * Visual-only evidence highlight. It must NEVER cover or intercept the
 * document text it points at:
 * - outline-only (transparent fill) so the underlying PDF text stays legible;
 * - pointer-events-none so text selection / scrolling passes straight through
 *   (finding navigation already lives in the inspector pane);
 * - a single compact pill parked OUTSIDE the box (flips below when near the
 *   page top) instead of a large tooltip over neighbouring text. The full
 *   quoted span is shown in the inspector, not duplicated here.
 */
export const EvidenceBox: React.FC<EvidenceBoxProps> = ({
  evidence,
  bounds,
  isSelected = true,
  tag,
}) => {
  const confidencePct = Math.round((evidence.confidence ?? 1) * 100);
  // Park the pill below the box when there is no headroom above it.
  const flipBelow = bounds.top < 30;

  return (
    <div
      style={{
        left: `${bounds.left}px`,
        top: `${bounds.top}px`,
        width: `${bounds.width}px`,
        height: `${bounds.height}px`,
        boxShadow: isSelected
          ? '0 0 0 2px var(--theme-unknown, #b45309), 0 0 10px 2px rgb(180 83 9 / 0.35)'
          : '0 0 0 1px var(--theme-brand, #1d4ed8)',
      }}
      className="absolute z-20 pointer-events-none rounded-[2px] bg-transparent"
      role="region"
      aria-label={`Evidence citation on page ${evidence.page_number}, ${confidencePct}% confidence`}
    >
      {/* Compact tag pill — outside the highlight, never over the text. */}
      <div
        className={`absolute left-0 z-30 flex items-center gap-1 whitespace-nowrap ${
          flipBelow ? 'top-full mt-1' : '-top-5'
        }`}
      >
        <span className="text-[9px] font-bold font-mono tracking-wider uppercase px-1.5 py-0.5 rounded-xs bg-theme-unknown text-white shadow">
          {tag || 'EVIDENCE'}
        </span>
        <span className="text-[9px] font-mono px-1 py-0.5 rounded-xs bg-theme-card/95 border border-theme-border text-theme-muted shadow">
          p{evidence.page_number} · {confidencePct}%
        </span>
      </div>
    </div>
  );
};
