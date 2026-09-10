import React, { useState } from 'react';
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

export const EvidenceBox: React.FC<EvidenceBoxProps> = ({
  evidence,
  bounds,
  isSelected = true,
  tag,
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
          ? 'bg-amber-400/25 border-2 border-amber-500 ring-2 ring-amber-500/40 shadow-sm'
          : 'bg-indigo-400/15 border border-indigo-500 hover:bg-indigo-400/25'
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="region"
      aria-label={`Evidence citation: ${evidence.quoted_span}`}
    >
      {/* Small Evidence Pill Header */}
      <div className="absolute -top-4 left-0 flex items-center gap-1 z-30">
        <span className="text-[9px] font-bold font-mono tracking-wider uppercase px-1.5 py-0.2 rounded-xs bg-amber-600 text-white shadow-xs">
          {tag || 'EVIDENCE'}
        </span>
      </div>

      {/* Floating Detail Tooltip on Hover or Selection */}
      {(isHovered || isSelected) && (
        <div className="absolute top-full left-0 mt-1.5 z-40 bg-slate-950/95 text-white text-[11px] p-2.5 rounded shadow-xl border border-slate-700 min-w-[240px] max-w-sm pointer-events-none backdrop-blur-xs space-y-1.5 animate-fade-in">
          <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-1 text-[10px] text-slate-400">
            <span className="font-semibold text-amber-400 uppercase tracking-wider font-mono">
              Verified Evidence
            </span>
            <span className="font-mono text-emerald-400">{confidencePct}% confidence</span>
          </div>
          <p className="font-medium text-slate-100 italic leading-snug font-mono">
            &ldquo;{evidence.quoted_span}&rdquo;
          </p>
          <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5 border-t border-slate-800/80">
            <span>
              Engine: <code className="text-slate-300 font-mono">{extractionMethod}</code>
            </span>
            <span className="font-mono">Page {evidence.page_number}</span>
          </div>
        </div>
      )}
    </div>
  );
};
