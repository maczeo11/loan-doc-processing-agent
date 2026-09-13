import { useState, useEffect, useRef, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { generateDemoPdfForDoc } from '../../utils/demoPdfGenerator';
import { fetchDocumentBlob } from '../../services/api';

// Initialize PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

export type PdfSourceType = 'real' | 'demo' | 'unavailable';

interface UsePdfDocumentOptions {
  docId: string;
  initialPage?: number;
  /**
   * Either an in-memory buffer, or `{applicationId, documentId}` which is
   * fetched through the authenticated API client. A plain URL string fetched
   * with a bare `fetch()` cannot carry the session and 401s once the dossier
   * routes are protected.
   */
  pdfSource?: Uint8Array | ArrayBuffer | { applicationId: string; documentId: string } | null;
  isDemoMode: boolean;
}

export function usePdfDocument({ docId, initialPage, pdfSource, isDemoMode }: UsePdfDocumentOptions) {
  const [pdfDocument, setPdfDocument] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(initialPage && initialPage >= 1 ? initialPage : 1);
  const [zoom, setZoom] = useState<number>(100);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRendering, setIsRendering] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceType, setSourceType] = useState<PdfSourceType>('unavailable');
  /** Object URL for a non-PDF (scanned image) document, else null. */
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [canvasDimensions, setCanvasDimensions] = useState<{ width: number; height: number }>({
    width: 595,
    height: 842,
  });
  const [unscaledDimensions, setUnscaledDimensions] = useState<{ width: number; height: number }>({
    width: 595,
    height: 842,
  });

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const renderTaskRef = useRef<pdfjsLib.RenderTask | null>(null);

  // Release the image object URL when the hook unmounts.
  useEffect(() => () => {
    setImageUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
  }, []);

  // Update page when docId or initialPage changes
  useEffect(() => {
    setCurrentPage(initialPage && initialPage >= 1 ? initialPage : 1);
  }, [docId, initialPage]);

  /**
   * Shrink-to-fit on first render only. Never enlarges: a page narrower than
   * the pane stays at its natural size rather than being blown up.
   */
  const autoFitOnLoad = useCallback(async (doc: pdfjsLib.PDFDocumentProxy) => {
    const container = containerRef.current;
    if (!container) return;
    try {
      const page = await doc.getPage(1);
      const unscaled = page.getViewport({ scale: 1 });
      const available = container.clientWidth - 48;
      if (available > 0 && unscaled.width > available) {
        const pct = Math.round((available / unscaled.width) * 100);
        setZoom(Math.max(50, Math.min(100, pct)));
      } else {
        setZoom(100);
      }
    } catch {
      setZoom(100);
    }
  }, []);

  // Load PDF document
  useEffect(() => {
    let isCancelled = false;
    setIsLoading(true);
    setError(null);
    setPdfDocument(null);
    setImageUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });

    async function loadDocument() {
      try {
        let loadingTask: pdfjsLib.PDFDocumentLoadingTask;

        if (pdfSource) {
          setSourceType('real');
          if ('applicationId' in pdfSource) {
            // Fetch bytes first so HTTP errors (401/404/422) surface distinctly
            // instead of pdf.js `MissingPDFException: Missing PDF "<url>"`.
            const { data, contentType } = await fetchDocumentBlob(
              pdfSource.applicationId,
              pdfSource.documentId
            );
            if (isCancelled) return;
            if (!data.byteLength) {
              throw new Error('Document is empty (0 bytes) — re-upload the file.');
            }
            // Scanned uploads are allowed (.jpg/.png/.tiff); render them as an
            // image rather than handing non-PDF bytes to pdf.js.
            if (!contentType.includes('pdf')) {
              const blob = new Blob([data], { type: contentType });
              const url = URL.createObjectURL(blob);
              setImageUrl((prev) => {
                if (prev) URL.revokeObjectURL(prev);
                return url;
              });
              setNumPages(1);
              setIsLoading(false);
              return;
            }
            setImageUrl(null);
            loadingTask = pdfjsLib.getDocument({ data });
          } else {
            setImageUrl(null);
            loadingTask = pdfjsLib.getDocument({ data: pdfSource });
          }
        } else if (isDemoMode) {
          setSourceType('demo');
          const demoBytes = generateDemoPdfForDoc(docId);
          loadingTask = pdfjsLib.getDocument({ data: demoBytes });
        } else {
          setSourceType('unavailable');
          setIsLoading(false);
          return;
        }

        const doc = await loadingTask.promise;
        if (!isCancelled) {
          setPdfDocument(doc);
          setNumPages(doc.numPages);
          setIsLoading(false);
          // Open at a zoom the page actually fits in. A fixed 100% meant an
          // A4 page (595pt) opened clipped on both sides in a narrow pane,
          // leaving the reviewer to zoom out before they could read anything.
          void autoFitOnLoad(doc);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          const errMsg = err instanceof Error ? err.message : 'Failed to load PDF document';
          setError(errMsg);
          setIsLoading(false);
        }
      }
    }

    loadDocument();

    return () => {
      isCancelled = true;
    };
  }, [docId, pdfSource, isDemoMode, autoFitOnLoad]);

  // Render current page onto canvas
  useEffect(() => {
    if (!pdfDocument || !canvasRef.current) return;

    let isCancelled = false;
    setIsRendering(true);

    async function renderPage() {
      try {
        // Cancel any pending render task
        if (renderTaskRef.current) {
          renderTaskRef.current.cancel();
          renderTaskRef.current = null;
        }

        const page = await pdfDocument!.getPage(currentPage);
        if (isCancelled || !canvasRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const scale = zoom / 100;
        const unscaledViewport = page.getViewport({ scale: 1 });
        setUnscaledDimensions({
          width: Math.floor(unscaledViewport.width),
          height: Math.floor(unscaledViewport.height),
        });
        const viewport = page.getViewport({ scale });
        const outputScale = window.devicePixelRatio || 1;

        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;
        setCanvasDimensions({
          width: Math.floor(viewport.width),
          height: Math.floor(viewport.height),
        });

        const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined;

        const renderContext = {
          canvasContext: ctx,
          transform,
          viewport,
        };

        const task = page.render(renderContext);
        renderTaskRef.current = task;
        await task.promise;

        if (!isCancelled) {
          setIsRendering(false);
          renderTaskRef.current = null;
        }
      } catch (err: unknown) {
        // Ignore normal cancellation errors when switching pages/zoom
        if (err && typeof err === 'object' && 'name' in err && (err as { name: string }).name === 'RenderingCancelledException') {
          return;
        }
        if (!isCancelled) {
          const errMsg = err instanceof Error ? err.message : 'Error rendering page canvas';
          setError(errMsg);
          setIsRendering(false);
        }
      }
    }

    renderPage();

    return () => {
      isCancelled = true;
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
        renderTaskRef.current = null;
      }
    };
  }, [pdfDocument, currentPage, zoom]);

  const nextPage = useCallback(() => {
    setCurrentPage((p) => Math.min(numPages, p + 1));
  }, [numPages]);

  const prevPage = useCallback(() => {
    setCurrentPage((p) => Math.max(1, p - 1));
  }, []);

  const goToPage = useCallback(
    (page: number) => {
      if (page >= 1 && page <= numPages) {
        setCurrentPage(page);
      }
    },
    [numPages]
  );

  const zoomIn = useCallback(() => {
    setZoom((z) => Math.min(200, z + 25));
  }, []);

  const zoomOut = useCallback(() => {
    setZoom((z) => Math.max(50, z - 25));
  }, []);

  const resetZoom = useCallback(() => {
    setZoom(100);
  }, []);

  /**
   * Scale the page to the actual viewport width rather than jumping to a fixed
   * 110%, which was a "fit width" control that never measured anything.
   */
  const fitWidth = useCallback(async () => {
    const container = containerRef.current;
    if (!pdfDocument || !container) {
      setZoom(100);
      return;
    }
    try {
      const page = await pdfDocument.getPage(currentPage);
      const unscaled = page.getViewport({ scale: 1 });
      // Leave room for the viewport's padding so the page never clips.
      const available = container.clientWidth - 48;
      if (available > 0 && unscaled.width > 0) {
        const pct = Math.round((available / unscaled.width) * 100);
        setZoom(Math.max(50, Math.min(200, pct)));
      }
    } catch {
      setZoom(100);
    }
  }, [pdfDocument, currentPage]);

  return {
    canvasRef,
    containerRef,
    canvasDimensions,
    unscaledDimensions,
    pdfDocument,
    imageUrl,
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
  };
}
