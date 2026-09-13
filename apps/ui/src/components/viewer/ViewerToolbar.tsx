import React from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2, FileSearch } from 'lucide-react';
import type { PdfSourceType } from './usePdfDocument';

interface ViewerToolbarProps {
  docTitle: string;
  docId: string;
  currentPage: number;
  numPages: number;
  zoom: number;
  sourceType: PdfSourceType;
  onPrevPage: () => void;
  onNextPage: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
  onFitWidth: () => void;
}

export const ViewerToolbar: React.FC<ViewerToolbarProps> = ({
  docTitle,
  docId,
  currentPage,
  numPages,
  zoom,
  sourceType,
  onPrevPage,
  onNextPage,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  onFitWidth,
}) => {
  const getSourceBadge = () => {
    switch (sourceType) {
      case 'real':
        return (
          <span className="px-2 py-0.5 rounded-xs text-[10px] font-bold bg-theme-pass-bg text-theme-pass border border-theme-pass-border shrink-0">
            LIVE PDF
          </span>
        );
      case 'demo':
        return (
          <span className="px-2 py-0.5 rounded-xs text-[10px] font-bold bg-theme-unknown-bg text-theme-unknown border border-theme-unknown-border shrink-0">
            DEMO PDF (SYNTHETIC)
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-xs text-[10px] font-bold bg-theme-panel text-theme-muted border border-theme-border shrink-0">
            SOURCE UNAVAILABLE
          </span>
        );
    }
  };

  return (
    <div className="min-h-[48px] py-1 bg-theme-header border-b border-theme-border px-3 sm:px-4 flex flex-wrap items-center justify-between gap-2 shadow-xs shrink-0 transition-colors duration-200">
      {/* Document Info & Source Badge */}
      <div className="flex items-center gap-2 min-w-0 max-w-full sm:max-w-md truncate">
        <FileSearch className="w-4 h-4 text-theme-brand shrink-0" />
        <span className="text-xs font-serif font-bold text-theme-primary truncate">
          {docTitle}
        </span>
        <span className="font-mono text-[10px] bg-theme-panel text-theme-muted px-1.5 py-0.5 rounded-xs border border-theme-border shrink-0">
          {docId}
        </span>
        {getSourceBadge()}
      </div>

      {/* Page & Zoom Controls */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-3 shrink-0 ml-auto">
        {/* Page Switcher */}
        <div className="flex items-center gap-1 bg-theme-panel border border-theme-border rounded-xs p-0.5">
          <button
            type="button"
            onClick={onPrevPage}
            disabled={currentPage <= 1}
            className="p-1 hover:bg-theme-card rounded-xs text-theme-primary disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
            title="Previous Page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-mono font-semibold text-theme-primary px-2 min-w-[70px] text-center tabular-nums">
            {numPages > 0 ? `${currentPage} / ${numPages}` : '-'}
          </span>
          <button
            type="button"
            onClick={onNextPage}
            disabled={currentPage >= numPages}
            className="p-1 hover:bg-theme-card rounded-xs text-theme-primary disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
            title="Next Page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1 bg-theme-panel border border-theme-border rounded-xs p-0.5">
          <button
            type="button"
            onClick={onZoomOut}
            disabled={zoom <= 50}
            className="p-1 hover:bg-theme-card rounded-xs text-theme-primary disabled:opacity-30 transition-colors cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onResetZoom}
            className="text-xs font-mono font-semibold text-theme-primary px-1.5 hover:bg-theme-card rounded-xs min-w-[45px] text-center tabular-nums transition-colors cursor-pointer"
            title="Reset to 100%"
          >
            {zoom}%
          </button>
          <button
            type="button"
            onClick={onZoomIn}
            disabled={zoom >= 200}
            className="p-1 hover:bg-theme-card rounded-xs text-theme-primary disabled:opacity-30 transition-colors cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onFitWidth}
            className="p-1 hover:bg-theme-card rounded-xs text-theme-muted hover:text-theme-primary border-l border-theme-border pl-1 transition-colors cursor-pointer"
            title="Fit Width"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
