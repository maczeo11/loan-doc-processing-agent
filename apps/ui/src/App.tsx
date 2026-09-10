import { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/layout/Header';
import { LeftDossierPane } from './components/layout/LeftDossierPane';
import { RightInspectorPane } from './components/layout/RightInspectorPane';
import { PdfViewer } from './components/viewer/PdfViewer';
import { KeyboardShortcutsModal } from './components/common/KeyboardShortcutsModal';
import { ReviewActionModal } from './components/review/ReviewActionModal';
import { DocumentUploadModal } from './components/navigation/DocumentUploadModal';
import { CreateDossierModal } from './components/navigation/CreateDossierModal';
import { getDocumentTitle } from './utils/documentHelper';
import { EvidenceNavigationProvider, useEvidenceNavigation } from './context/EvidenceNavigationContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import type { LoanApplicationState } from './types/contracts';
import type { LoanApplication, DossierDocument } from './types/application';
import type { EvidenceRef } from './types/evidence';
import type { ReviewDecision } from './types/api';
import { getEvidenceKey } from './utils/coordinates';
import { api } from './services/api';

// Backend requires reviewer_id; the active persona profile supplies it
// (verified JWT claims remain the production item).
const FALLBACK_REVIEWER_ID = 'underwriter@finscan.ai';
// Poll only while the pipeline is still running (spec: >=2s interval).
const POLL_INTERVAL_MS = 2500;

export interface DossierListItem {
  application_id: string;
  applicant_name: string;
  loan_amount: number;
  status: string;
}

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
      // page_count / ocr_route / verified are intentionally absent:
      // the backend does not provide them and we never synthesize them.
    } as DossierDocument;
  });

  const history = state.status_history || [];
  // Header facts come from authoritative columns (see GET /applications/{id}),
  // exposed on the state payload as applicant_name / loan_amount.
  const headerBag = state as LoanApplicationState & {
    applicant_name?: string;
    loan_amount?: number;
  };

  return {
    id: state.application_id,
    applicant_name: headerBag.applicant_name || state.applicant?.full_name || '—',
    pan_masked: state.applicant?.pan_number || '—',
    loan_amount: typeof headerBag.loan_amount === 'number' ? headerBag.loan_amount : 0,
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
  // No selection and no dossier until the backend answers — the desk never
  // invents records. Empty DB => intentional empty state, not demo data.
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [dossierState, setDossierState] = useState<LoanApplicationState | null>(null);
  const [apps, setApps] = useState<DossierListItem[]>([]);
  const [appsLoading, setAppsLoading] = useState<boolean>(true);
  const [appsError, setAppsError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // Modal + pipeline action state
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<ReviewDecision | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

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
  const application = useMemo(
    () => (dossierState ? toLoanApplication(dossierState) : null),
    [dossierState]
  );

  // Review SLA anchors at the moment the pipeline became reviewable —
  // never at creation (processing time is not the reviewer's debt).
  const slaAnchor = useMemo(() => {
    const history = dossierState?.status_history || [];
    const ready = [...history]
      .reverse()
      .find((t) => t.to_status === 'READY_FOR_REVIEW');
    return ready ? ready.timestamp : null;
  }, [dossierState]);

  const loadApps = useCallback(async (selectFirst = false) => {
    setAppsLoading(true);
    setAppsError(null);
    try {
      const list = await api.listApplications();
      setApps(list || []);
      if (selectFirst && list && list.length > 0) {
        setSelectedAppId((prev) => prev || list[0].application_id);
      }
    } catch (err) {
      setAppsError(err instanceof Error ? err.message : 'Failed to reach API');
      setApps([]);
    } finally {
      setAppsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadApps(true);
  }, [loadApps]);

  const fetchApplicationData = useCallback(async (quiet = false) => {
    if (!selectedAppId) return;
    if (!quiet) {
      setIsLoading(true);
      setLoadError(null);
    }
    try {
      const live = await api.getApplication(selectedAppId);
      setDossierState(live as LoanApplicationState);
      setLoadError(null);
      const ids = (live as LoanApplicationState).document_ids || [];
      if (ids.length > 0) onSelectDoc(ids[0]);
      if (!quiet) setNotification(null);
    } catch (err) {
      if (!quiet) {
        setLoadError(err instanceof Error ? err.message : 'Failed to fetch application');
      }
    } finally {
      if (!quiet) setIsLoading(false);
    }
  }, [selectedAppId, onSelectDoc]);

  useEffect(() => {
    fetchApplicationData();
  }, [fetchApplicationData]);

  // Single status poll while the pipeline runs (one GET per tick: <=30/min).
  useEffect(() => {
    if (!dossierState) return;
    if (dossierState.status !== 'QUEUED' && dossierState.status !== 'PROCESSING') return;
    const timer = setInterval(() => {
      fetchApplicationData(true);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [dossierState, dossierState?.status, fetchApplicationData]);

  const handleSelectDoc = (docId: string) => {
    onSelectDoc(docId);
  };

  const handleSelectAppId = (appId: string) => {
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
    const finding = dossierState?.findings?.[idx];
    if (finding && finding.supporting_evidence.length > 0) {
      markInspected(finding.supporting_evidence[0]);
    }
  };

  const handleTriggerAction = (decision: ReviewDecision) => {
    setReviewDecision(decision);
  };

  const handleCreateDossier = async (values: { applicant_name: string; loan_amount: number; loan_purpose?: string }) => {
    const resp = await api.createApplication({
      applicant_name: values.applicant_name,
      loan_amount: values.loan_amount,
      loan_purpose: values.loan_purpose,
    });
    setCreateOpen(false);
    await loadApps();
    setSelectedAppId(resp.application_id);
    setNotification(`Dossier ${resp.application_id} created — upload documents to begin.`);
  };

  const handleUploadDocument = async (file: File, docTypeHint?: string) => {
    await api.uploadDocument(selectedAppId, file, docTypeHint);
    await fetchApplicationData(true);
  };

  const handleRunPipeline = async () => {
    setIsProcessing(true);
    try {
      const resp = await api.processApplication(selectedAppId);
      setNotification(`Pipeline queued: ${resp.job_id}. Status polls every 2.5s.`);
      await fetchApplicationData(true);
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Failed to queue pipeline');
    } finally {
      setIsProcessing(false);
    }
  };

  const { user } = useAuth();
  const reviewerId = user?.email || FALLBACK_REVIEWER_ID;

  const handleSubmitReview = async (notes: string) => {
    setIsSubmitting(true);
    try {
      if (!reviewDecision) return;
      const resp = await api.submitReview(selectedAppId, {
        decision: reviewDecision,
        reviewer_id: reviewerId,
        notes,
      });
      const liveStatus = (resp as { status?: LoanApplicationState['status'] }).status;
      setDossierState((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: liveStatus ?? prev.status,
          reviewer_decision: reviewDecision,
          reviewer_notes: notes,
        };
      });
      setNotification(`Review submitted: ${reviewDecision} (${resp.application_id})`);
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

      const findings = dossierState?.findings || [];
      // Sign-off hotkeys mirror the inspector gate: READY_FOR_REVIEW + findings.
      const canSign =
        dossierState?.status === 'READY_FOR_REVIEW' && findings.length > 0;
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
          const docIds = dossierState?.document_ids || [];
          const curIdx = docIds.indexOf(selectedDocId);
          if (curIdx < docIds.length - 1) onSelectDoc(docIds[curIdx + 1]);
          break;
        }
        case '[': {
          const docIds = dossierState?.document_ids || [];
          const curIdx = docIds.indexOf(selectedDocId);
          if (curIdx > 0) onSelectDoc(docIds[curIdx - 1]);
          break;
        }
        case 'a':
        case 'A':
          if (canSign) setReviewDecision('APPROVED');
          break;
        case 'r':
        case 'R':
          if (canSign) setReviewDecision('REJECTED');
          break;
        case 'n':
        case 'N':
          if (canSign) setReviewDecision('NEEDS_INFO');
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
    dossierState?.classified_types?.[selectedDocId]
  );

  // ---- Render states: loading / backend error / empty / ready ----
  if (appsLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-theme-app text-theme-secondary text-sm font-mono">
        Connecting to underwriting API…
      </div>
    );
  }

  if (appsError) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-theme-app">
        <div className="max-w-md p-6 rounded border border-theme-border bg-theme-card text-center space-y-3">
          <p className="text-sm font-bold text-theme-primary font-mono">Backend unreachable</p>
          <p className="text-xs text-theme-secondary">{appsError}</p>
          <p className="text-xs text-theme-muted">Start the API, then retry. No demo data is shown.</p>
          <button
            type="button"
            onClick={() => loadApps(true)}
            className="px-4 py-2 rounded bg-theme-brand text-white text-xs font-mono font-bold"
          >
            Retry connection
          </button>
        </div>
      </div>
    );
  }

  if (apps.length === 0) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-theme-app">
        <div className="max-w-md p-6 rounded border border-theme-border bg-theme-card text-center space-y-3">
          <p className="text-sm font-bold text-theme-primary font-mono">No applications yet</p>
          <p className="text-xs text-theme-secondary">
            Create your first dossier to start the underwriting workflow.
          </p>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="px-4 py-2 rounded bg-theme-brand text-white text-xs font-mono font-bold"
          >
            + New dossier
          </button>
        </div>
        <CreateDossierModal
          isOpen={createOpen}
          onClose={() => setCreateOpen(false)}
          onCreate={handleCreateDossier}
        />
      </div>
    );
  }

  if (!application) {
    if (loadError) {
      return (
        <div className="h-screen w-screen flex items-center justify-center bg-theme-app">
          <div className="max-w-md p-6 rounded border border-theme-border bg-theme-card text-center space-y-3">
            <p className="text-sm font-bold text-theme-primary font-mono">Could not load dossier</p>
            <p className="text-xs text-theme-secondary">{loadError}</p>
            <button
              type="button"
              onClick={() => fetchApplicationData()}
              className="px-4 py-2 rounded bg-theme-brand text-white text-xs font-mono font-bold"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-theme-app text-theme-secondary text-sm font-mono">
        {isLoading ? 'Loading dossier…' : 'Select a dossier to begin.'}
      </div>
    );
  }

  const showSla = application.status === 'READY_FOR_REVIEW';

  return (
    <div className="h-screen w-screen flex flex-col bg-theme-app text-theme-primary font-sans overflow-hidden transition-colors duration-200">
      {/* Swiss Banking Header */}
      <Header
        selectedAppId={selectedAppId}
        availableApps={apps}
        onSelectAppId={handleSelectAppId}
        onNewDossier={() => setCreateOpen(true)}
        status={application.status}
        slaAnchor={slaAnchor}
        showSla={showSla}
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
          onOpenUpload={() => setUploadOpen(true)}
          onRunPipeline={handleRunPipeline}
          canRunPipeline={application.status === 'UPLOADED' && application.documents.length > 0}
          isProcessing={isProcessing}
          width={280}
        />

        {/* Center Pane: PDF.js Viewer */}
        <div className="flex-1 h-full min-w-0">
          <PdfViewer
            docId={selectedDocId}
            docTitle={currentDocTitle}
            pdfSource={`/applications/${encodeURIComponent(selectedAppId)}/documents/${encodeURIComponent(selectedDocId)}`}
            isDemoMode={false}
          />
        </div>

        {/* Right Pane: Inspector (Findings / Facts / CAM / Policy) */}
        <RightInspectorPane
          application={application}
          activeEvidenceKey={activeEvidenceKey}
          focusedFindingIndex={focusedFindingIndex}
          onSelectFindingIndex={handleSelectFindingIndex}
          onSelectEvidence={handleSelectEvidence}
          onTriggerAction={handleTriggerAction}
          inspectedKeys={inspectedKeys}
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

      {/* Dossier document upload */}
      <DocumentUploadModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleUploadDocument}
        applicationId={selectedAppId}
      />

      {/* New dossier */}
      <CreateDossierModal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreate={handleCreateDossier}
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
    <ThemeProvider>
      <AuthProvider>
        <EvidenceNavigationProvider onSelectDocument={handleSelectDocument}>
          <AppInner selectedDocId={selectedDocId} onSelectDoc={handleSelectDocument} />
        </EvidenceNavigationProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
