import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2, FileSearch, Layers } from 'lucide-react';

interface ViewerPaneProps {
  selectedDocId: string;
  docTitle?: string;
}

export const ViewerPane: React.FC<ViewerPaneProps> = ({
  selectedDocId,
  docTitle = 'Selected Document',
}) => {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const totalPages = 3;
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  const handlePrevPage = () => setCurrentPage((p) => Math.max(1, p - 1));
  const handleNextPage = () => setCurrentPage((p) => Math.min(totalPages, p + 1));
  const handleZoomIn = () => setZoomLevel((z) => Math.min(200, z + 25));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(50, z - 25));
  const handleResetZoom = () => setZoomLevel(100);

  return (
    <main className="w-full h-full flex flex-col bg-slate-100 overflow-hidden">
      {/* Viewer Toolbar */}
      <div className="h-12 bg-white border-b border-slate-200 px-4 flex items-center justify-between shadow-sm shrink-0">
        <div className="flex items-center gap-2 truncate">
          <FileSearch className="w-4 h-4 text-indigo-600 shrink-0" />
          <span className="text-xs font-semibold text-slate-800 truncate">
            {docTitle}
          </span>
          <span className="font-mono text-[11px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded shrink-0">
            {selectedDocId}
          </span>
        </div>

        {/* Page & Zoom Controls */}
        <div className="flex items-center gap-4">
          {/* Page Controls */}
          <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg p-0.5">
            <button
              onClick={handlePrevPage}
              disabled={currentPage <= 1}
              className="p-1 hover:bg-slate-200 rounded text-slate-600 disabled:opacity-30"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-medium text-slate-700 px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={handleNextPage}
              disabled={currentPage >= totalPages}
              className="p-1 hover:bg-slate-200 rounded text-slate-600 disabled:opacity-30"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg p-0.5">
            <button
              onClick={handleZoomOut}
              className="p-1 hover:bg-slate-200 rounded text-slate-600"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={handleResetZoom}
              className="text-xs font-medium text-slate-700 px-1.5 hover:bg-slate-200 rounded"
              title="Reset Zoom"
            >
              {zoomLevel}%
            </button>
            <button
              onClick={handleZoomIn}
              className="p-1 hover:bg-slate-200 rounded text-slate-600"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={handleResetZoom}
              className="p-1 hover:bg-slate-200 rounded text-slate-600 border-l border-slate-200 pl-1"
              title="Fit to Width"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* PDF Canvas Viewport Container */}
      <div className="flex-1 overflow-auto p-6 flex justify-center items-start">
        <div
          style={{ width: `${Math.round(595 * (zoomLevel / 100))}px`, minHeight: `${Math.round(842 * (zoomLevel / 100))}px` }}
          className="bg-white rounded-lg shadow-md border border-slate-200 flex flex-col relative transition-all"
        >
          {/* Watermark Banner */}
          <div className="w-full bg-amber-50 border-b border-amber-200 px-4 py-1.5 text-center">
            <span className="text-[11px] font-bold tracking-wider text-amber-800">
              SYNTHETIC DEMO — NOT VALID
            </span>
          </div>

          {/* Viewer Placeholder Body */}
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="w-16 h-16 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-4 shadow-sm">
              <Layers className="w-8 h-8" />
            </div>
            <h3 className="text-sm font-bold text-slate-800 mb-1">
              Document Viewer Viewport
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mb-4">
              Direct browser canvas rendering with <span className="font-semibold text-slate-700">pdf.js</span> and dynamic <span className="font-semibold text-slate-700">EvidenceRef</span> bounding-box highlights will mount here in Step 3.
            </p>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-left w-full max-w-xs space-y-1.5 text-xs text-slate-600">
              <div className="flex justify-between">
                <span className="text-slate-400">Document Name:</span>
                <span className="font-semibold text-slate-800 truncate max-w-[170px]">{docTitle}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Document ID:</span>
                <span className="font-mono font-medium text-slate-700">{selectedDocId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Current Page:</span>
                <span className="font-medium text-slate-700">{currentPage} of {totalPages}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Render Target:</span>
                <span className="font-medium text-indigo-600">HTML5 Canvas (pdf.js)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};
