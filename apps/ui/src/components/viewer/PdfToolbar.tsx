import React from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Eye, EyeOff, FileText, CheckCircle2 } from 'lucide-react';
import { DossierDocument } from '../../types/application';

interface PdfToolbarProps {
  document?: DossierDocument;
  scale: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
  showOverlays: boolean;
  onToggleOverlays: () => void;
  activeEvidenceKey: string | null;
  onClearActiveEvidence: () => void;
}

export const PdfToolbar: React.FC<PdfToolbarProps> = ({
  document,
  scale,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  showOverlays,
  onToggleOverlays,
  activeEvidenceKey,
  onClearActiveEvidence,
}) => {
  return (
    <div className="h-10 min-h-[40px] bg-white border-b border-[#E3DDD3] px-3.5 flex items-center justify-between select-none z-20 shadow-sm">
      {/* Left: Active Document Name & Badges */}
      <div className="flex items-center gap-2.5 min-w-0">
        <FileText className="w-4 h-4 text-stone-700 flex-shrink-0" />
        <span className="text-xs font-serif font-bold text-stone-900 truncate max-w-[220px]">
          {document?.name || 'No document selected'}
        </span>
        {document && (
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#F8F6F1] text-stone-700 border border-[#E3DDD3]">
            {document.document_type}
          </span>
        )}
      </div>

      {/* Center: Active Citation Pill if jumping to evidence */}
      {activeEvidenceKey && (
        <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#FDF8EE] border border-[#B45309]/50 text-[#92400E] text-xs animate-fade-in shadow-xs">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#B45309]" />
          <span className="font-mono text-[11px] font-medium">Active Evidence Citation Focused</span>
          <button
            onClick={onClearActiveEvidence}
            className="ml-1 text-[#B45309] hover:text-stone-900 text-[10px] underline cursor-pointer"
          >
            Clear
          </button>
        </div>
      )}

      {/* Right: Zoom & Overlay Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleOverlays}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors ${
            showOverlays
              ? 'bg-[#FDF8EE] border-[#B45309] text-[#92400E]'
              : 'bg-white border-[#E3DDD3] text-stone-600 hover:bg-[#F8F6F1]'
          }`}
          title="Toggle Evidence Bounding Boxes"
        >
          {showOverlays ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
          <span className="text-[11px] font-medium hidden sm:inline">Evidence Boxes</span>
        </button>

        <div className="h-4 w-px bg-[#E3DDD3]" />

        <div className="flex items-center gap-1 bg-[#FBF9F5] border border-[#E3DDD3] rounded px-1 py-0.5">
          <button
            onClick={onZoomOut}
            className="p-1 rounded hover:bg-stone-200 text-stone-700 hover:text-stone-900 transition-colors"
            title="Zoom Out (-)"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs font-mono text-stone-800 px-1.5 min-w-[42px] text-center tabular-nums font-semibold">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={onZoomIn}
            className="p-1 rounded hover:bg-stone-200 text-stone-700 hover:text-stone-900 transition-colors"
            title="Zoom In (+)"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onResetZoom}
            className="p-1 rounded hover:bg-stone-200 text-stone-500 hover:text-stone-900 transition-colors ml-0.5"
            title="Reset Zoom (0)"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
};
