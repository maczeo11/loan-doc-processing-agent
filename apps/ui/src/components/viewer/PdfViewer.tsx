import React, { useEffect } from 'react';
import { AlertTriangle, FileX, Loader2, CheckCircle, X } from 'lucide-react';
import { usePdfDocument } from './usePdfDocument';
import { ViewerToolbar } from './ViewerToolbar';
import { BoundingBoxOverlay } from './BoundingBoxOverlay';
import { useEvidenceNavigation } from '../../context/EvidenceNavigationContext';

interface PdfViewerProps {
  docId: string;
  docTitle: string;
  pdfSource?: Uint8Array | ArrayBuffer | string | null;
  isDemoMode: boolean;
}

export const PdfViewer: React.FC<PdfViewerProps> = ({
  docId,
  docTitle,
  pdfSource,
  isDemoMode,
}) => {
  const {
    canvasRef,
    canvasDimensions,
    pdfDocument,
    numPages,
    currentPage,
    zoom,
    isLoading,
    isRendering,
    error,
    sourceType,
    nextPage,
    prevPage,
    goToPage,
    zoomIn,
    zoomOut,
    resetZoom,
    fitWidth,
  } = usePdfDocument({ docId, pdfSource, isDemoMode });

  const {
    activeEvidence,
    targetPageToNavigate,
    clearTargetPage,
    clearActiveEvidence,
  } = useEvidenceNavigation();

  // Navigate to target page when requested by evidence citation.
  // NOTE: numPages may still reflect the previous document right after a
  // document switch — keep the target pending until the new document loads
  // instead of clearing it, otherwise the highlight is silently lost.
  useEffect(() => {
    if (
      targetPageToNavigate === null ||
      !pdfDocument ||
      !activeEvidence ||
      activeEvidence.document_id !== docId
    ) {
      return;
    }
    if (currentPage === targetPageToNavigate) {
      clearTargetPage();
      return;
    }
    if (targetPageToNavigate >= 1 && targetPageToNavigate <= numPages) {
      goToPage(targetPageToNavigate);
      clearTargetPage();
    }
  }, [
    targetPageToNavigate,
    pdfDocument,
    activeEvidence,
    docId,
    currentPage,
    numPages,
    goToPage,
    clearTargetPage,
  ]);

  const hasActiveEvidenceOnCurrentPage =
    activeEvidence &&
    activeEvidence.document_id === docId &&
    activeEvidence.page_number === currentPage;

  return (
    <main className="w-full h-full flex flex-col bg-[#F5F2EB] overflow-hidden">
      {/* Top Toolbar */}
      <ViewerToolbar
        docTitle={docTitle}
        docId={docId}
        currentPage={currentPage}
        numPages={numPages}
        zoom={zoom}
        sourceType={sourceType}
        onPrevPage={prevPage}
        onNextPage={nextPage}
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onResetZoom={resetZoom}
        onFitWidth={fitWidth}
      />

      {/* Active Evidence Notification Bar (Compact Banking Style) */}
      {hasActiveEvidenceOnCurrentPage && (
        <div className="bg-amber-50/95 border-b border-amber-200 px-4 py-1.5 flex items-center justify-between text-xs text-amber-900 shadow-2xs shrink-0 backdrop-blur-xs">
          <div className="flex items-center gap-2 truncate">
            <CheckCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span className="font-bold text-[11px] uppercase tracking-wider bg-amber-200 text-amber-900 px-1.5 py-0.2 rounded-xs">
              Verified Evidence
            </span>
            <span className="italic font-medium truncate">
              "{activeEvidence.quoted_span}"
            </span>
            <span className="text-[10px] text-amber-700 font-mono hidden sm:inline">
              ({Math.round((activeEvidence.confidence ?? 1) * 100)}% conf | {activeEvidence.extraction_method || 'pymupdf_native'})
            </span>
          </div>
          <button
            type="button"
            onClick={clearActiveEvidence}
            className="text-amber-700 hover:text-amber-950 p-1 rounded hover:bg-amber-100 shrink-0 ml-2"
            title="Clear active evidence highlight"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Viewport */}
      <div className="flex-1 overflow-auto p-6 flex justify-center items-start bg-[#F5F2EB]">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 text-center">
            <Loader2 className="w-8 h-8 text-stone-500 animate-spin mb-3" />
            <p className="text-xs font-serif font-bold text-stone-800">Loading document with PDF.js...</p>
            <p className="text-[11px] text-stone-500 mt-0.5 font-mono">Parsing document structure</p>
          </div>
        ) : error ? (
          <div className="bg-white rounded-sm shadow-md border border-[#FECACA] p-8 text-center max-w-md my-auto">
            <div className="w-12 h-12 rounded-full bg-[#FEF2F2] border border-[#FECACA] flex items-center justify-center text-[#991B1B] mx-auto mb-3">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-serif font-bold text-stone-900 mb-1">Failed to Render PDF</h3>
            <p className="text-xs text-[#991B1B] bg-[#FEF2F2] p-2 rounded-sm border border-[#FECACA] font-mono mb-3 break-all">
              {error}
            </p>
            <p className="text-[11px] text-stone-500">
              The PDF could not be processed by the browser canvas renderer. Verify document integrity or source data.
            </p>
          </div>
        ) : sourceType === 'unavailable' ? (
          <div className="bg-white rounded-sm shadow-md border border-[#E3DDD3] p-8 text-center max-w-md my-auto">
            <div className="w-12 h-12 rounded-full bg-[#F8F6F1] border border-[#E3DDD3] flex items-center justify-center text-stone-400 mx-auto mb-3">
              <FileX className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-serif font-bold text-stone-900 mb-1">Document Source Unavailable</h3>
            <p className="text-xs text-stone-600 mb-3">
              The live backend does not currently expose a GET document download endpoint. Toggle to <strong className="text-stone-900">Demo Dossier</strong> to view synthetic client-rendered documents.
            </p>
            <div className="bg-[#F8F6F1] border border-[#E3DDD3] rounded-sm p-2 text-[11px] text-stone-700 font-mono">
              Document ID: {docId}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center relative">
            {/* Watermark header banner */}
            <div
              style={{ width: `${canvasDimensions.width}px` }}
              className="bg-amber-50 border border-amber-200 rounded-t-lg px-4 py-1 text-center shadow-xs transition-all"
            >
              <span className="text-[10px] font-bold tracking-wider text-amber-800 uppercase">
                SYNTHETIC DEMO — NOT VALID (FinScan AI)
              </span>
            </div>

            {/* Rendering Indicator */}
            {isRendering && (
              <div className="absolute top-10 right-4 z-30 bg-stone-900/80 text-white text-[10px] font-mono px-2.5 py-1 rounded-full flex items-center gap-1.5 shadow">
                <Loader2 className="w-3 h-3 animate-spin text-amber-200" />
                <span>Rendering canvas...</span>
              </div>
            )}

            {/* Canvas Frame with Absolute Bounding Box Overlay */}
            <div
              style={{
                width: `${canvasDimensions.width}px`,
                height: `${canvasDimensions.height}px`,
              }}
              className="bg-white rounded-b-sm shadow-lg border border-t-0 border-[#D5CFC5] relative overflow-hidden transition-all"
            >
              {/* HTML5 Canvas rendered by PDF.js */}
              <canvas ref={canvasRef} className="block w-full h-full" />

              {/* Bounding Box Highlights Layer */}
              <BoundingBoxOverlay
                activeEvidence={activeEvidence}
                canvasWidth={canvasDimensions.width}
                canvasHeight={canvasDimensions.height}
                currentDocId={docId}
                currentPage={currentPage}
              />
            </div>
          </div>
        )}
      </div>
    </main>
  );
};
