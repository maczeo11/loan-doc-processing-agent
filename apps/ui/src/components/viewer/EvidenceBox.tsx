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
}

export const EvidenceBox: React.FC<EvidenceBoxProps> = ({
  evidence,
  bounds,
  isSelected = true,
}) => {
  const [isHovered, setIsHovered] = useState<boolean>(false);

  const confidencePct = Math.round((evidence.confidence ?? 1) * 100);
  const extractionMethod = evidence.extraction_method || 'pymupdf_native';

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
          ? 'bg-amber-400/20 border-2 border-amber-600 ring-2 ring-amber-500/40 ring-offset-1 shadow-xs'
          : 'bg-indigo-400/15 border border-indigo-500 hover:bg-indigo-400/25'
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="region"
      aria-label={`Evidence citation: ${sanitizePiiInText(evidence.quoted_span || '')}`}
    >
      {/* Small Evidence Pill Header */}
      <div className="absolute -top-3.5 left-0 flex items-center gap-1">
        <span className="text-[9px] font-bold tracking-wider uppercase px-1 py-0.2 rounded-xs bg-amber-600 text-white shadow-xs">
          EVIDENCE
        </span>
      </div>

      {/* Floating Detail Tooltip on Hover or Selection */}
      {(isHovered || isSelected) && (
        <div className="absolute top-full left-0 mt-1 z-30 bg-slate-900/95 text-white text-[11px] p-2.5 rounded-lg shadow-xl border border-slate-700 min-w-[220px] max-w-sm pointer-events-none backdrop-blur-xs space-y-1">
          <div className="flex items-center justify-between gap-2 border-b border-slate-700 pb-1 text-[10px] text-slate-400">
            <span className="font-semibold text-amber-400 uppercase">Verified Evidence</span>
            <span className="font-mono">{confidencePct}% confidence</span>
          </div>
          <p className="font-medium text-slate-100 italic leading-snug">
            "{sanitizePiiInText(evidence.quoted_span || '')}"
          </p>
          <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
            <span>Source: <code className="text-slate-300">{extractionMethod}</code></span>
            <span>p. {evidence.page_number}</span>
          </div>
        </div>
      )}
    </div>
  );
};
