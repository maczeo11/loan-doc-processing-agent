import React, { createContext, useContext, useState, useCallback } from 'react';
import type { EvidenceRef } from '../types/contracts';

interface EvidenceNavigationContextType {
  activeEvidence: EvidenceRef | null;
  activeRuleId: string | null;
  targetPageToNavigate: number | null;
  navigateToEvidence: (evidence: EvidenceRef, ruleId?: string) => void;
  clearActiveEvidence: () => void;
  clearTargetPage: () => void;
}

const EvidenceNavigationContext = createContext<EvidenceNavigationContextType | undefined>(undefined);

export const EvidenceNavigationProvider: React.FC<{
  children: React.ReactNode;
  onSelectDocument?: (docId: string) => void;
}> = ({ children, onSelectDocument }) => {
  const [activeEvidence, setActiveEvidence] = useState<EvidenceRef | null>(null);
  const [activeRuleId, setActiveRuleId] = useState<string | null>(null);
  const [targetPageToNavigate, setTargetPageToNavigate] = useState<number | null>(null);

  const navigateToEvidence = useCallback(
    (evidence: EvidenceRef, ruleId?: string) => {
      setActiveEvidence(evidence);
      setActiveRuleId(ruleId ?? null);
      setTargetPageToNavigate(evidence.page_number);
      if (onSelectDocument) {
        onSelectDocument(evidence.document_id);
      }
    },
    [onSelectDocument]
  );

  const clearActiveEvidence = useCallback(() => {
    setActiveEvidence(null);
    setActiveRuleId(null);
  }, []);

  const clearTargetPage = useCallback(() => {
    setTargetPageToNavigate(null);
  }, []);

  return (
    <EvidenceNavigationContext.Provider
      value={{
        activeEvidence,
        activeRuleId,
        targetPageToNavigate,
        navigateToEvidence,
        clearActiveEvidence,
        clearTargetPage,
      }}
    >
      {children}
    </EvidenceNavigationContext.Provider>
  );
};

export function useEvidenceNavigation(): EvidenceNavigationContextType {
  const context = useContext(EvidenceNavigationContext);
  if (!context) {
    throw new Error('useEvidenceNavigation must be used within an EvidenceNavigationProvider');
  }
  return context;
}
