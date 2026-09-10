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
    activeRuleId,
    targetPageToNavigate,
    clearTargetPage,
    clearActiveEvidence,
  } = useEvidenceNavigation();

  // Navigate to target page when requested by evidence citation.
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
    <main className="w-full h-full flex flex-col bg-theme-desk overflow-hidden transition-colors duration-200">
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

      {/* Active Evidence Notification Bar */}
      {hasActiveEvidenceOnCurrentPage && (
        <div className="bg-amber-500/15 border-b border-amber-500/40 px-4 py-1.5 flex items-center justify-between text-xs text-amber-700 dark:text-amber-300 shadow-2xs shrink-0 backdrop-blur-xs">
          <div className="flex items-center gap-2 truncate">
            <CheckCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="font-bold text-[11px] uppercase tracking-wider bg-amber-500/30 text-amber-800 dark:text-amber-200 px-1.5 py-0.2 rounded-xs font-mono">
              Verified Evidence
            </span>
            <span className="italic font-medium truncate font-mono">
              &ldquo;{activeEvidence.quoted_span}&rdquo;
            </span>
            <span className="text-[10px] text-amber-700 dark:text-amber-400 font-mono hidden sm:inline">
              ({Math.round((activeEvidence.confidence ?? 1) * 100)}% conf |{' '}
              {activeEvidence.extraction_method || 'pymupdf_native'})
            </span>
          </div>
          <button
            type="button"
            onClick={clearActiveEvidence}
            className="text-amber-700 dark:text-amber-300 hover:text-amber-950 dark:hover:text-white p-1 rounded hover:bg-amber-500/20 shrink-0 ml-2 cursor-pointer"
            title="Clear active evidence highlight"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Viewport */}
      <div className="flex-1 overflow-auto p-6 flex justify-center items-start bg-theme-desk transition-colors duration-200">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 text-center">
            <Loader2 className="w-8 h-8 text-theme-muted animate-spin mb-3" />
            <p className="text-xs font-serif font-bold text-theme-primary">
              Loading document with PDF.js...
            </p>
            <p className="text-[11px] text-theme-muted mt-0.5 font-mono">
              Parsing document structure & text layer
            </p>
          </div>
        ) : error ? (
          <div className="bg-theme-card rounded-xs shadow-md border border-theme-flag-border p-8 text-center max-w-md my-auto">
            <div className="w-12 h-12 rounded-full bg-theme-flag-bg border border-theme-flag-border flex items-center justify-center text-theme-flag mx-auto mb-3">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-serif font-bold text-theme-primary mb-1">
              Failed to Render PDF
            </h3>
            <p className="text-xs text-theme-flag bg-theme-flag-bg p-2 rounded-xs border border-theme-flag-border font-mono mb-3 break-all">
              {error}
            </p>
            <p className="text-[11px] text-theme-muted">
              The PDF could not be processed by the browser canvas renderer. Verify document integrity or source data.
            </p>
          </div>
        ) : sourceType === 'unavailable' ? (
          <div className="bg-theme-card rounded-xs shadow-md border border-theme-border p-8 text-center max-w-md my-auto">
            <div className="w-12 h-12 rounded-full bg-theme-panel border border-theme-border flex items-center justify-center text-theme-muted mx-auto mb-3">
              <FileX className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-serif font-bold text-theme-primary mb-1">
              Document Source Unavailable
            </h3>
            <p className="text-xs text-theme-secondary mb-3">
              The live backend does not currently expose a GET document download endpoint. Toggle to{' '}
              <strong className="text-theme-primary">Demo Dossier</strong> to view synthetic client-rendered documents.
            </p>
            <div className="bg-theme-panel border border-theme-border rounded-xs p-2 text-[11px] text-theme-primary font-mono">
              Document ID: {docId}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center relative shadow-xl">
            {/* Watermark header banner */}
            <div
              style={{ width: `${canvasDimensions.width}px` }}
              className="bg-amber-500/15 border border-amber-500/30 rounded-t px-4 py-1 text-center shadow-xs transition-all backdrop-blur-xs"
            >
              <span className="text-[10px] font-bold font-mono tracking-wider text-amber-700 dark:text-amber-300 uppercase">
                SYNTHETIC DEMO — NOT VALID (FinScan AI)
              </span>
            </div>

            {/* Rendering Indicator */}
            {isRendering && (
              <div className="absolute top-10 right-4 z-30 bg-slate-900/85 text-white text-[10px] font-mono px-2.5 py-1 rounded-full flex items-center gap-1.5 shadow">
                <Loader2 className="w-3 h-3 animate-spin text-amber-300" />
                <span>Rendering canvas...</span>
              </div>
            )}

            {/* Canvas Frame with Absolute Bounding Box Overlay */}
            <div
              style={{
                width: `${canvasDimensions.width}px`,
                height: `${canvasDimensions.height}px`,
              }}
              className="bg-white rounded-b-sm shadow-2xl border border-t-0 border-theme-border relative overflow-hidden transition-all"
            >
              {/* HTML5 Canvas rendered by PDF.js */}
              <canvas ref={canvasRef} className="block w-full h-full" />

              {/* Bounding Box Highlights Layer */}
              <BoundingBoxOverlay
                activeEvidence={activeEvidence}
                activeRuleId={activeRuleId}
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
