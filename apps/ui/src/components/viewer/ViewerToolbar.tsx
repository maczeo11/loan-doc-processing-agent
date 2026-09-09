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
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 shrink-0">
            LIVE PDF
          </span>
        );
      case 'demo':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300 shrink-0">
            DEMO PDF (SYNTHETIC)
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-300 shrink-0">
            SOURCE UNAVAILABLE
          </span>
        );
    }
  };

  return (
    <div className="h-12 bg-white border-b border-slate-200 px-4 flex items-center justify-between shadow-xs shrink-0">
      {/* Document Info & Source Badge */}
      <div className="flex items-center gap-2 truncate">
        <FileSearch className="w-4 h-4 text-indigo-600 shrink-0" />
        <span className="text-xs font-bold text-slate-800 truncate">
          {docTitle}
        </span>
        <span className="font-mono text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded shrink-0">
          {docId}
        </span>
        {getSourceBadge()}
      </div>

      {/* Page & Zoom Controls */}
      <div className="flex items-center gap-3">
        {/* Page Switcher */}
        <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg p-0.5">
          <button
            type="button"
            onClick={onPrevPage}
            disabled={currentPage <= 1}
            className="p-1 hover:bg-slate-200 rounded text-slate-600 disabled:opacity-30 disabled:hover:bg-transparent"
            title="Previous Page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-semibold text-slate-700 px-2 min-w-[70px] text-center">
            {numPages > 0 ? `${currentPage} / ${numPages}` : '-'}
          </span>
          <button
            type="button"
            onClick={onNextPage}
            disabled={currentPage >= numPages}
            className="p-1 hover:bg-slate-200 rounded text-slate-600 disabled:opacity-30 disabled:hover:bg-transparent"
            title="Next Page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg p-0.5">
          <button
            type="button"
            onClick={onZoomOut}
            disabled={zoom <= 50}
            className="p-1 hover:bg-slate-200 rounded text-slate-600 disabled:opacity-30"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onResetZoom}
            className="text-xs font-semibold text-slate-700 px-1.5 hover:bg-slate-200 rounded min-w-[45px] text-center"
            title="Reset to 100%"
          >
            {zoom}%
          </button>
          <button
            type="button"
            onClick={onZoomIn}
            disabled={zoom >= 200}
            className="p-1 hover:bg-slate-200 rounded text-slate-600 disabled:opacity-30"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onFitWidth}
            className="p-1 hover:bg-slate-200 rounded text-slate-600 border-l border-slate-200 pl-1"
            title="Fit Width"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
