import { useState, useEffect, useRef, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { generateDemoPdfForDoc } from '../../utils/demoPdfGenerator';

// Initialize PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

export type PdfSourceType = 'real' | 'demo' | 'unavailable';

interface UsePdfDocumentOptions {
  docId: string;
  pdfSource?: Uint8Array | ArrayBuffer | string | null;
  isDemoMode: boolean;
}

export function usePdfDocument({ docId, pdfSource, isDemoMode }: UsePdfDocumentOptions) {
  const [pdfDocument, setPdfDocument] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(100);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRendering, setIsRendering] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceType, setSourceType] = useState<PdfSourceType>('unavailable');
  const [canvasDimensions, setCanvasDimensions] = useState<{ width: number; height: number }>({
    width: 595,
    height: 842,
  });

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const renderTaskRef = useRef<pdfjsLib.RenderTask | null>(null);

  // Reset to page 1 whenever docId changes
  useEffect(() => {
    setCurrentPage(1);
  }, [docId]);

  // Load PDF document
  useEffect(() => {
    let isCancelled = false;
    setIsLoading(true);
    setError(null);
    setPdfDocument(null);

    async function loadDocument() {
      try {
        let loadingTask: pdfjsLib.PDFDocumentLoadingTask;

        if (pdfSource) {
          setSourceType('real');
          if (typeof pdfSource === 'string') {
            loadingTask = pdfjsLib.getDocument(pdfSource);
          } else {
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
  }, [docId, pdfSource, isDemoMode]);

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

  const fitWidth = useCallback(() => {
    setZoom(110);
  }, []);

  return {
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
  };
}
