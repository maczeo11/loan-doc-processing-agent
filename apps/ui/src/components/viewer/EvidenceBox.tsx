import React, { useState } from 'react';
import type { EvidenceRef } from '../../types/contracts';
import { sanitizePiiInText } from '../../utils/pii';

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

export const EvidenceBox: React.FC<EvidenceBoxProps> = ({
  evidence,
  bounds,
  isSelected = true,
  tag,
}) => {
  const [isHovered, setIsHovered] = useState<boolean>(false);

  const confidencePct = Math.round((evidence.confidence ?? 1) * 100);
  const extractionMethod = evidence.extraction_method || 'pymupdf_native';
  // Quoted spans come straight off the document and routinely contain PAN,
  // Aadhaar and account numbers — never render one unmasked.
  const safeSpan = sanitizePiiInText(evidence.quoted_span || '');

  return (
    <div
      style={{
        left: `${bounds.left}px`,
        top: `${bounds.top}px`,
        width: `${bounds.width}px`,
        height: `${bounds.height}px`,
      }}
      className={`absolute z-20 transition-all pointer-events-auto cursor-pointer rounded-xs ${
        isSelected
          ? // bg-theme-unknown-bg (an opaque fill, not a tint) used to sit here
            // and painted a solid rectangle directly over the underlying PDF
            // text - completely hiding the very evidence the box points at.
            // A translucent wash (matching the unselected state's pattern
            // below) keeps the highlight visible while the text stays legible.
            'bg-theme-unknown/15 border-2 border-theme-unknown ring-2 ring-theme-unknown/40 shadow-sm'
          : 'bg-theme-brand/10 border border-theme-brand hover:bg-theme-brand/20'
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="region"
      aria-label={`Evidence citation: ${safeSpan}`}
    >
      {/* Small Evidence Pill Header */}
      <div className="absolute -top-4 left-0 flex items-center gap-1 z-30">
        <span className="text-[9px] font-bold font-mono tracking-wider uppercase px-1.5 py-0.5 rounded-xs bg-theme-unknown text-white shadow-xs">
          {tag || 'EVIDENCE'}
        </span>
      </div>

      {/* Floating Detail Tooltip on Hover or Selection */}
      {(isHovered || isSelected) && (
        <div className="absolute top-full left-0 mt-1.5 z-40 bg-theme-card text-theme-primary text-[11px] p-2.5 rounded-xs shadow-xl border border-theme-border-card min-w-[240px] max-w-sm pointer-events-none space-y-1.5 animate-fade-in">
          <div className="flex items-center justify-between gap-2 border-b border-theme-border pb-1 text-[10px] text-theme-muted">
            <span className="font-semibold text-theme-unknown uppercase tracking-wider font-mono">
              Verified Evidence
            </span>
            <span className="font-mono text-theme-pass">{confidencePct}% confidence</span>
          </div>
          <p className="font-medium text-theme-primary italic leading-snug font-mono">
            &ldquo;{safeSpan}&rdquo;
          </p>
          <div className="flex items-center justify-between text-[10px] text-theme-muted pt-0.5 border-t border-theme-border">
            <span>
              Engine: <code className="text-theme-secondary font-mono">{extractionMethod}</code>
            </span>
            <span className="font-mono">Page {evidence.page_number}</span>
          </div>
        </div>
      )}
    </div>
  );
};
