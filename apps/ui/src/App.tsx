import { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/layout/Header';
import { LeftDossierPane } from './components/layout/LeftDossierPane';
import { RightInspectorPane } from './components/layout/RightInspectorPane';
import { PdfViewer } from './components/viewer/PdfViewer';
import { KeyboardShortcutsModal } from './components/common/KeyboardShortcutsModal';
import { ReviewActionModal } from './components/review/ReviewActionModal';
import { NewApplicationModal, NewApplicationPayload } from './components/navigation/NewApplicationModal';
import { DashboardPage } from './components/DashboardPage';
import { LoginPage } from './components/auth/LoginPage';
import { getDemoDossier } from './data/mockDossier';
import { getDocumentTitle } from './utils/documentHelper';
import { EvidenceNavigationProvider, useEvidenceNavigation } from './context/EvidenceNavigationContext';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import type { LoanApplicationState } from './types/contracts';
import type { LoanApplication, DossierDocument } from './types/application';
import type { EvidenceRef } from './types/evidence';
import type { ReviewDecision } from './types/api';
import { getEvidenceKey } from './utils/coordinates';
import { api } from './services/api';
import { useAuth } from './context/AuthContext';

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

  const history = state.status_history || [];

  return {
    id: state.application_id,
    applicant_name: state.applicant?.full_name || 'Applicant',
    pan_masked: state.applicant?.pan_number || '—',
    loan_amount: 2500000, // Demo seed value: ₹ 25,00,000
    currency: 'INR',
    status: state.status,
    created_at: history[0]?.timestamp || new Date().toISOString(),
    updated_at: history.length > 0 ? history[history.length - 1].timestamp : undefined,
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
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [dossierState, setDossierState] = useState<LoanApplicationState>({
    application_id: 'NEW-DOSSIER',
    status: 'UPLOADED',
    status_history: [],
    document_ids: [],
    document_manifest: {},
    classified_types: {},
    applicant: null,
    payslip: null,
    bank_statement: null,
    tax_return: null,
    findings: [],
    missing_documents: [],
    retrieved_chunk_ids: [],
    summary_markdown: null,
    summary_grounded: false,
    review_paused: false,
    reviewer_decision: null,
    reviewer_notes: null,
    corrections_applied: [],
  });
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Modal state
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<ReviewDecision | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isNewAppModalOpen, setIsNewAppModalOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const { user, mode, isLoading: authLoading } = useAuth();
  const [liveApps, setLiveApps] = useState<Array<{ application_id: string; applicant_name: string; status: string }>>([]);

  const refreshLiveApps = useCallback(async () => {
    try {
      const apps = await api.listApplications();
      if (Array.isArray(apps)) {
        setLiveApps(apps);
        // Dashboard-first: do NOT auto-pick apps[0]; user opens explicitly.
      }
    } catch {
      // Backend offline or unreachable
    }
  }, []);

  useEffect(() => {
    refreshLiveApps();
  }, [refreshLiveApps]);

  // Finding focus + inspection tracking
  const [focusedFindingIndex, setFocusedFindingIndex] = useState<number>(0);
  const [inspectedKeys, setInspectedKeys] = useState<Set<string>>(new Set());

  // Evidence navigation
  const { activeEvidence, navigateToEvidence } = useEvidenceNavigation();
  const activeEvidenceKey = activeEvidence ? getEvidenceKey(activeEvidence) : null;

  const markInspected = useCallback((ev: EvidenceRef) => {
    setInspectedKeys((prev) => {
      const next = new Set(prev);
      next.add(getEvidenceKey(ev));
      return next;
    });
  }, []);

  // Convert state to LoanApplication for Swiss components
  const application = useMemo(() => toLoanApplication(dossierState), [dossierState]);

  const fetchApplicationData = useCallback(async (isPolling = false) => {
    if (!selectedAppId) return;
    if (!isPolling) setIsLoading(true);
    try {
      // 1. Try to fetch from live backend API first
      try {
        const liveState = await api.getApplication(selectedAppId);
        if (liveState && liveState.application_id) {
          setDossierState(liveState as LoanApplicationState);
          if (liveState.document_ids && liveState.document_ids.length > 0 && !selectedDocId) {
            onSelectDoc(liveState.document_ids[0]);
          }
          if (!isPolling) {
            setNotification(`Live dossier loaded: ${selectedAppId} (${liveState.applicant?.full_name || 'Underwriting'})`);
          }
          return;
        }
      } catch {
        // Fall back to demo preset if backend doesn't have this application
      }

      // 2. Load demo preset for the chosen archetype
      const dossier = getDemoDossier(selectedAppId);
      setDossierState(dossier);
      if (dossier.document_ids && dossier.document_ids.length > 0 && !selectedDocId) {
        onSelectDoc(dossier.document_ids[0]);
      }
      if (!isPolling) {
        setNotification(`Demo preset loaded: ${selectedAppId}`);
      }
    } catch (err) {
      if (!isPolling) {
        setNotification(err instanceof Error ? err.message : 'Failed to fetch application');
      }
    } finally {
      if (!isPolling) setIsLoading(false);
    }
  }, [selectedAppId, onSelectDoc, selectedDocId]);

  useEffect(() => {
    if (selectedAppId) {
      fetchApplicationData();
    }
  }, [selectedAppId, fetchApplicationData]);

  // Live polling: automatically poll backend every 2s while job is QUEUED or PROCESSING
  useEffect(() => {
    const isQueuedOrProcessing = dossierState.status === 'QUEUED' || dossierState.status === 'PROCESSING';
    if (!isQueuedOrProcessing) return;

    const interval = setInterval(() => {
      fetchApplicationData(true);
      refreshLiveApps();
    }, 2000);

    return () => clearInterval(interval);
  }, [dossierState.status, fetchApplicationData, refreshLiveApps]);

  const handleSelectDoc = (docId: string) => {
    onSelectDoc(docId);
  };

  const handleSelectAppId = (appId: string) => {
    // Reset doc selection so a stale demo `doc-app-form` never collides with
    // live `DOC-XXXXXXXX` ids (which would 404 with the same MissingPDF symptom).
    if (appId !== selectedAppId) {
      onSelectDoc('');
    }
    setSelectedAppId(appId);
  };

  const handleSelectEvidence = useCallback(
    (ev: EvidenceRef, ruleId?: string) => {
      markInspected(ev);
      navigateToEvidence(ev, ruleId);
    },
    [markInspected, navigateToEvidence]
  );

  const handleSelectFindingIndex = (idx: number) => {
    setFocusedFindingIndex(idx);
    const finding = dossierState.findings?.[idx];
    if (finding && finding.supporting_evidence.length > 0) {
      markInspected(finding.supporting_evidence[0]);
    }
  };

  const handleTriggerAction = (decision: ReviewDecision) => {
    setReviewDecision(decision);
  };

  const handleSubmitReview = async (notes: string) => {
    if (!reviewDecision) return;
    setIsSubmitting(true);
    try {
      try {
        await api.submitReview(selectedAppId, {
          decision: reviewDecision,
          reviewer_id: user?.email || 'underwriter-bhanu',
          notes,
          corrections: [],
        });
        await fetchApplicationData();
        refreshLiveApps();
        setNotification(`Review submitted: ${reviewDecision} (persisted to PostgreSQL)`);
      } catch {
        // Offline fallback for demo presets
        setDossierState((prev) => ({
          ...prev,
          status: reviewDecision === 'NEEDS_INFO' ? 'NEEDS_INFORMATION' : 'REVIEWED',
          reviewer_decision: reviewDecision,
          reviewer_notes: notes,
        }));
        setNotification(`Review updated (preset): ${reviewDecision}`);
      }
      setReviewDecision(null);
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Error submitting review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUploadDocument = async (file: File, docTypeHint?: string) => {
    try {
      let targetAppId = selectedAppId;

      // If user hasn't created or selected an application yet, automatically initialize one for them!
      if (!targetAppId || targetAppId === 'NEW-DOSSIER' || targetAppId.startsWith('DEMO-')) {
        const defaultName = file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " ").toUpperCase();
        const created = await api.createApplication({
          applicant_name: `Applicant (${defaultName})`,
          loan_amount: 2500000,
          loan_purpose: 'Retail Credit',
        });
        targetAppId = created.application_id;
        setSelectedAppId(targetAppId);
        await refreshLiveApps();
      }

      const res = await api.uploadDocument(targetAppId, file, docTypeHint);
      setNotification(`Document uploaded: ${file.name} (${res.document_id}) to ${targetAppId}`);
      await fetchApplicationData();
      refreshLiveApps();
      if (res.document_id) {
        onSelectDoc(res.document_id);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to upload document';
      setNotification(msg);
      throw err;
    }
  };

  const handleCreateApplication = async (payload: NewApplicationPayload) => {
    try {
      const res = await api.createApplication({
        applicant_name: payload.applicant_name,
        loan_amount: payload.loan_amount,
        loan_purpose: payload.loan_purpose,
      });
      setNotification(`Application ${res.application_id} created successfully.`);
      await refreshLiveApps();
      onSelectDoc('');
      setSelectedAppId(res.application_id);
      setIsNewAppModalOpen(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create application';
      setNotification(msg);
      throw err;
    }
  };

  const handleProcessDossier = async () => {
    setIsProcessing(true);
    try {
      const res = await api.processApplication(selectedAppId);
      setNotification(`Pipeline enqueued for ${selectedAppId} (Job: ${res.job_id}). Polling status...`);
      await fetchApplicationData();
      refreshLiveApps();
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Failed to trigger pipeline');
    } finally {
      setIsProcessing(false);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return;

      const findings = dossierState.findings || [];
      // Sign-off hotkeys mirror the inspector gate: READY_FOR_REVIEW + findings.
      const canSignOff =
        dossierState.status === 'READY_FOR_REVIEW' && findings.length > 0;
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
        case 'Enter': {
          const finding = findings[focusedFindingIndex];
          if (finding && finding.supporting_evidence.length > 0) {
            e.preventDefault();
            handleSelectEvidence(finding.supporting_evidence[0], finding.rule_id);
          }
          break;
        }
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
          if (canSignOff) setReviewDecision('APPROVED');
          break;
        case 'r':
        case 'R':
          if (canSignOff) setReviewDecision('REJECTED');
          break;
        case 'n':
        case 'N':
          if (canSignOff) setReviewDecision('NEEDS_INFO');
          break;
        case 'Escape':
          setShortcutsOpen(false);
          setReviewDecision(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dossierState, selectedDocId, onSelectDoc, focusedFindingIndex, handleSelectEvidence]);

  const currentDocTitle = getDocumentTitle(
    selectedDocId,
    dossierState.classified_types?.[selectedDocId]
  );

  const isDemoPreset = ['APP-25195', 'APP-68210', 'APP-10492'].includes(selectedAppId);
  // Guard empty app/doc + use same-origin relative URL (Vite proxy in dev,
  // FastAPI-served dist in prod). encodeURIComponent prevents path breakage.
  // Falls through to `unavailable` empty state instead of pdf.js MissingPDF.
  const pdfSource =
    selectedAppId && selectedDocId && !isDemoPreset
      ? `/applications/${encodeURIComponent(selectedAppId)}/documents/${encodeURIComponent(selectedDocId)}`
      : undefined;

  // Real loan-app start: dashboard first when no dossier selected.
  if (!selectedAppId) {
    if (mode === 'google' && !user && !authLoading) {
      return <LoginPage onLoggedIn={() => refreshLiveApps()} />;
    }
    return (
      <div className="h-screen w-screen flex flex-col bg-theme-app overflow-hidden">
        {mode === 'google' && authLoading ? (
          <div className="m-auto text-xs text-theme-muted">Verifying session…</div>
        ) : (
          <DashboardPage
            apps={liveApps}
            onRefresh={refreshLiveApps}
            onOpen={(id) => handleSelectAppId(id)}
            onNew={() => setIsNewAppModalOpen(true)}
          />
        )}
        <NewApplicationModal
          isOpen={isNewAppModalOpen}
          onClose={() => setIsNewAppModalOpen(false)}
          onSubmit={handleCreateApplication}
        />
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-theme-app text-theme-primary font-sans overflow-hidden transition-colors duration-200">
      {/* Workspace bar: back to desk + Swiss Banking Header */}
      <div className="flex items-center gap-2 px-3 sm:px-5 pt-2">
        <button
          type="button"
          onClick={() => handleSelectAppId('')}
          className="text-[11px] font-mono px-2 py-1 rounded-xs border border-theme-border hover:bg-theme-panel text-theme-secondary hover:text-theme-primary shrink-0"
          title="Back to Dossier Desk"
        >
          ← Desk
        </button>
      </div>
      {/* Swiss Banking Header */}
      <Header
        selectedAppId={selectedAppId}
        onSelectAppId={handleSelectAppId}
        status={application.status}
        createdAt={application.created_at}
        onOpenShortcuts={() => setShortcutsOpen(true)}
        liveApplications={liveApps}
        onRefresh={refreshLiveApps}
        onOpenNewApplication={() => setIsNewAppModalOpen(true)}
      />

      {/* Dossier load indicator — polling refreshes stay silent, only an
          explicit fetch surfaces here. */}
      {isLoading && (
        <div
          role="status"
          aria-live="polite"
          className="bg-theme-panel border-b border-theme-border text-theme-secondary text-[11px] font-mono px-4 py-1 flex items-center gap-2 shrink-0"
        >
          <span className="inline-block w-2 h-2 rounded-full bg-theme-brand animate-ping" />
          <span>Loading dossier…</span>
        </div>
      )}

      {/* Notification Toast (theme-aware) */}
      {notification && (
        <div className="bg-theme-card border-b border-theme-border text-theme-primary text-xs px-4 py-1.5 flex items-center justify-between shrink-0">
          <span className="truncate">{notification}</span>
          <button
            onClick={() => setNotification(null)}
            className="text-theme-muted hover:text-theme-primary ml-4 font-bold shrink-0"
          >
            ×
          </button>
        </div>
      )}

      {/* Three-Pane Swiss Reviewer Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane: Dossier Documents (hidden on small, overlay via drawer pattern) */}
        <div className="hidden md:block shrink-0">
          <LeftDossierPane
            application={application}
            activeDocId={selectedDocId}
            onSelectDocId={handleSelectDoc}
            onUploadDocument={handleUploadDocument}
            width={280}
          />
        </div>

        {/* Center Pane: PDF.js Viewer */}
        <div className="flex-1 h-full min-w-0">
          <PdfViewer
            docId={selectedDocId}
            docTitle={currentDocTitle}
            pdfSource={pdfSource}
            isDemoMode={isDemoPreset}
          />
        </div>

        {/* Right Pane: Inspector (collapses below lg) */}
        <div className="hidden lg:block shrink-0">
          <RightInspectorPane
            application={application}
            activeEvidenceKey={activeEvidenceKey}
            focusedFindingIndex={focusedFindingIndex}
            onSelectFindingIndex={handleSelectFindingIndex}
            onSelectEvidence={handleSelectEvidence}
            onTriggerAction={handleTriggerAction}
            onProcessDossier={handleProcessDossier}
            isProcessing={isProcessing}
            inspectedKeys={inspectedKeys}
            width={390}
          />
        </div>
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

      {/* New Application Modal */}
      <NewApplicationModal
        isOpen={isNewAppModalOpen}
        onClose={() => setIsNewAppModalOpen(false)}
        onSubmit={handleCreateApplication}
      />
    </div>
  );
}

/**
 * Root App component: owns the selected document (so evidence navigation can
 * switch documents) and wraps with AuthProvider + EvidenceNavigationProvider.
 */
export default function App() {
  // Start with no doc selected so first paint shows the `unavailable` empty
  // state instead of building /applications//documents/doc-app-form.
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const handleSelectDocument = useCallback((docId: string) => {
    setSelectedDocId(docId);
  }, []);

  return (
    <ThemeProvider>
      <AuthProvider>
        <EvidenceNavigationProvider onSelectDocument={handleSelectDocument}>
          <AppInner selectedDocId={selectedDocId} onSelectDoc={handleSelectDocument} />
        </EvidenceNavigationProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
