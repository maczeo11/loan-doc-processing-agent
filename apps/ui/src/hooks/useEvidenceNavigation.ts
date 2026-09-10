import { useState, useCallback, useRef } from 'react';
import { EvidenceRef } from '../types/evidence';
import { getEvidenceKey } from '../utils/coordinates';

export function useEvidenceNavigation(initialDocId: string = '') {
  const [activeDocumentId, setActiveDocumentId] = useState<string>(initialDocId);
  const [activePageNumber, setActivePageNumber] = useState<number>(1);
  const [activeEvidenceKey, setActiveEvidenceKey] = useState<string | null>(null);
  const pulseTimerRef = useRef<number | null>(null);

  const jumpToEvidence = useCallback((evidence: EvidenceRef) => {
    const docId = evidence.document_id;
    const pageNum = evidence.page_number;
    const key = getEvidenceKey(evidence);

    setActiveDocumentId(docId);
    setActivePageNumber(pageNum);
    setActiveEvidenceKey(key);

    // Smooth scroll to the target page element
    setTimeout(() => {
      const el = document.getElementById(`pdf-page-${pageNum}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 150);

    // Reset pulse timer for 4 seconds attention glow
    if (pulseTimerRef.current) {
      window.clearTimeout(pulseTimerRef.current);
    }
    pulseTimerRef.current = window.setTimeout(() => {
      // Keep selected or softly fade pulse
      pulseTimerRef.current = null;
    }, 4000);
  }, []);

  const clearActiveEvidence = useCallback(() => {
    setActiveEvidenceKey(null);
    if (pulseTimerRef.current) {
      window.clearTimeout(pulseTimerRef.current);
      pulseTimerRef.current = null;
    }
  }, []);

  return {
    activeDocumentId,
    setActiveDocumentId,
    activePageNumber,
    setActivePageNumber,
    activeEvidenceKey,
    jumpToEvidence,
    clearActiveEvidence,
  };
}
