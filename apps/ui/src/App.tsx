import { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/layout/Header';
import { LeftDossierPane } from './components/layout/LeftDossierPane';
import { RightInspectorPane } from './components/layout/RightInspectorPane';
import { PdfViewer } from './components/viewer/PdfViewer';
import { KeyboardShortcutsModal } from './components/common/KeyboardShortcutsModal';
import { ReviewActionModal } from './components/review/ReviewActionModal';
import { DEMO_DOSSIER_APP_25195 } from './data/mockDossier';
import { getDocumentTitle } from './utils/documentHelper';
import { EvidenceNavigationProvider, useEvidenceNavigation } from './context/EvidenceNavigationContext';
import { AuthProvider } from './context/AuthContext';
import type { LoanApplicationState } from './types/contracts';
import type { LoanApplication, DossierDocument } from './types/application';
import type { EvidenceRef } from './types/evidence';
import type { ReviewDecision } from './types/api';
import { getEvidenceKey } from './utils/coordinates';

/**
 * Adapter: convert LoanApplicationState (backend contract) → LoanApplication (UI component model).
 * The new Swiss layout components expect the richer LoanApplication interface.
 */
function toLoanApplication(state: LoanApplicationState): LoanApplication {
  const docIds = state.document_ids || [];
  const classified = state.classified_types || {};

  const documents: DossierDocument[] = docIds.map((id) => {
    const docType = classified[id] || 'document';
    // Map classified_types to DossierDocument.document_type enum values
    let mappedType = 'DOCUMENT';
    if (docType.includes('payslip')) mappedType = 'PAYSLIP';
    else if (docType.includes('bank')) mappedType = 'BANK_STATEMENT';
    else if (docType.includes('tax') || docType.includes('itr')) mappedType = 'TAX_RETURN';
    else if (docType.includes('id') || docType.includes('pan') || docType.includes('kyc')) mappedType = 'ID_CARD';
    else if (docType.includes('application')) mappedType = 'APPLICATION_FORM';

    return {
      id,
      name: getDocumentTitle(id, docType),
      document_type: mappedType,
      page_count: mappedType === 'APPLICATION_FORM' ? 2 : mappedType === 'BANK_STATEMENT' ? 3 : 1,
      ocr_route: id === 'doc-pan-card' ? 'paddle' : 'native',
      verified: true,
    } as DossierDocument;
  });

  return {
    id: state.application_id,
    applicant_name: state.applicant?.full_name || 'Applicant',
    pan_masked: state.applicant?.pan_number || '—',
    loan_amount: 2500000, // Demo seed value: ₹ 25,00,000
    currency: 'INR',
    status: state.status,
    created_at: state.status_history?.[0]?.timestamp || new Date().toISOString(),
    documents,
    findings: state.findings || [],
    payslip_facts: state.payslip || undefined,
    bank_facts: state.bank_statement || undefined,
    tax_facts: state.tax_return || undefined,
    applicant_facts: state.applicant || undefined,
    memo_markdown: state.summary_markdown || undefined,
    reviewer_decision: state.reviewer_decision || null,
    reviewer_notes: state.reviewer_notes || null,
  };
}

/**
 * Inner App component that has access to EvidenceNavigation context.
 */
function AppInner({
  selectedDocId,
  onSelectDoc,
}: {
  selectedDocId: string;
  onSelectDoc: (docId: string) => void;
}) {
  const [selectedAppId, setSelectedAppId] = useState<string>('APP-25195');
  const [dossierState, setDossierState] = useState<LoanApplicationState>(DEMO_DOSSIER_APP_25195);
  const [_isLoading, setIsLoading] = useState<boolean>(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Modal state
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<ReviewDecision | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Finding focus state
  const [focusedFindingIndex, setFocusedFindingIndex] = useState<number>(0);

  // Evidence navigation
  const { activeEvidence, navigateToEvidence } = useEvidenceNavigation();
  const activeEvidenceKey = activeEvidence ? getEvidenceKey(activeEvidence) : null;

  // Convert state to LoanApplication for Swiss components
  const application = useMemo(() => toLoanApplication(dossierState), [dossierState]);

  const fetchApplicationData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Always use demo data for now (backend not yet serving GET /applications/{id})
      setDossierState(DEMO_DOSSIER_APP_25195);
      if (DEMO_DOSSIER_APP_25195.document_ids && DEMO_DOSSIER_APP_25195.document_ids.length > 0) {
        onSelectDoc(DEMO_DOSSIER_APP_25195.document_ids[0]);
      }
      setNotification('Loaded demo dossier for APP-25195');
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Failed to fetch application');
    } finally {
      setIsLoading(false);
    }
  }, [selectedAppId, onSelectDoc]);

  useEffect(() => {
    fetchApplicationData();
  }, [fetchApplicationData]);

  const handleSelectDoc = (docId: string) => {
    onSelectDoc(docId);
  };

  const handleSelectAppId = (appId: string) => {
    setSelectedAppId(appId);
  };

  const handleSelectEvidence = (ev: EvidenceRef) => {
    navigateToEvidence(ev);
  };

  const handleTriggerAction = (decision: ReviewDecision) => {
    setReviewDecision(decision);
  };

  const handleSubmitReview = async (notes: string) => {
    setIsSubmitting(true);
    try {
      setDossierState((prev) => ({
        ...prev,
        status: reviewDecision === 'NEEDS_INFO' ? 'NEEDS_INFORMATION' : 'REVIEWED',
        reviewer_decision: reviewDecision,
        reviewer_notes: notes,
      }));
      setNotification(`Review submitted: ${reviewDecision}`);
      setReviewDecision(null);
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Error submitting review');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return;

      const findings = dossierState.findings || [];
      switch (e.key) {
        case '?':
          setShortcutsOpen((prev) => !prev);
          break;
        case 'j':
        case 'ArrowDown':
          e.preventDefault();
          setFocusedFindingIndex((prev) => Math.min(prev + 1, findings.length - 1));
          break;
        case 'k':
        case 'ArrowUp':
          e.preventDefault();
          setFocusedFindingIndex((prev) => Math.max(prev - 1, 0));
          break;
        case ']': {
          const docIds = dossierState.document_ids || [];
          const curIdx = docIds.indexOf(selectedDocId);
          if (curIdx < docIds.length - 1) onSelectDoc(docIds[curIdx + 1]);
          break;
        }
        case '[': {
          const docIds = dossierState.document_ids || [];
          const curIdx = docIds.indexOf(selectedDocId);
          if (curIdx > 0) onSelectDoc(docIds[curIdx - 1]);
          break;
        }
        case 'a':
        case 'A':
          if (dossierState.status !== 'REVIEWED') setReviewDecision('APPROVED');
          break;
        case 'r':
        case 'R':
          if (dossierState.status !== 'REVIEWED') setReviewDecision('REJECTED');
          break;
        case 'n':
        case 'N':
          if (dossierState.status !== 'REVIEWED') setReviewDecision('NEEDS_INFO');
          break;
        case 'Escape':
          setShortcutsOpen(false);
          setReviewDecision(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dossierState, selectedDocId, onSelectDoc]);

  const currentDocTitle = getDocumentTitle(
    selectedDocId,
    dossierState.classified_types?.[selectedDocId]
  );

  return (
    <div className="h-screen w-screen flex flex-col bg-[#F8F6F1] font-sans overflow-hidden">
      {/* Swiss Banking Header */}
      <Header
        selectedAppId={selectedAppId}
        onSelectAppId={handleSelectAppId}
        status={application.status}
        createdAt={application.created_at}
        onOpenShortcuts={() => setShortcutsOpen(true)}
      />

      {/* Notification Toast */}
      {notification && (
        <div className="bg-stone-800 text-white text-xs px-4 py-1.5 flex items-center justify-between shrink-0">
          <span>{notification}</span>
          <button
            onClick={() => setNotification(null)}
            className="text-stone-400 hover:text-white ml-4 font-bold"
          >
            ×
          </button>
        </div>
      )}

      {/* Three-Pane Swiss Reviewer Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane: Dossier Documents */}
        <LeftDossierPane
          application={application}
          activeDocId={selectedDocId}
          onSelectDocId={handleSelectDoc}
          width={280}
        />

        {/* Center Pane: PDF.js Viewer */}
        <div className="flex-1 h-full min-w-0">
          <PdfViewer
            docId={selectedDocId}
            docTitle={currentDocTitle}
            isDemoMode={true}
          />
        </div>

        {/* Right Pane: Inspector (Findings / Facts / CAM / Policy) */}
        <RightInspectorPane
          application={application}
          activeEvidenceKey={activeEvidenceKey}
          focusedFindingIndex={focusedFindingIndex}
          onSelectFindingIndex={setFocusedFindingIndex}
          onSelectEvidence={handleSelectEvidence}
          onTriggerAction={handleTriggerAction}
          width={390}
        />
      </div>

      {/* Keyboard Shortcuts Modal */}
      <KeyboardShortcutsModal
        isOpen={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />

      {/* Review Action Modal (HITL Sign-Off) */}
      <ReviewActionModal
        isOpen={!!reviewDecision}
        decision={reviewDecision}
        applicationId={selectedAppId}
        onClose={() => setReviewDecision(null)}
        onSubmit={handleSubmitReview}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}

/**
 * Root App component: owns the selected document (so evidence navigation can
 * switch documents) and wraps with AuthProvider + EvidenceNavigationProvider.
 */
export default function App() {
  const [selectedDocId, setSelectedDocId] = useState<string>('doc-app-form');
  const handleSelectDocument = useCallback((docId: string) => {
    setSelectedDocId(docId);
  }, []);

  return (
    <AuthProvider>
      <EvidenceNavigationProvider onSelectDocument={handleSelectDocument}>
        <AppInner selectedDocId={selectedDocId} onSelectDoc={handleSelectDocument} />
      </EvidenceNavigationProvider>
    </AuthProvider>
  );
}
