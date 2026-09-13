import { useState, useEffect, useCallback, useMemo } from 'react';
import { Sparkles, Play, Loader2, ArrowRight } from 'lucide-react';
import { Header } from './components/layout/Header';
import { LeftDossierPane } from './components/layout/LeftDossierPane';
import { RightInspectorPane, TabType } from './components/layout/RightInspectorPane';
import { PdfViewer } from './components/viewer/PdfViewer';
import { KeyboardShortcutsModal } from './components/common/KeyboardShortcutsModal';
import { ReviewActionModal } from './components/review/ReviewActionModal';
import { NewApplicationModal, NewApplicationPayload } from './components/navigation/NewApplicationModal';
import { DashboardPage, DashboardApp } from './components/DashboardPage';
import { LoginPage } from './components/auth/LoginPage';
import { getDemoDossier, isDemoDossierId } from './data/mockDossier';
import { getDocumentTitle } from './utils/documentHelper';
import { EvidenceNavigationProvider, useEvidenceNavigation } from './context/EvidenceNavigationContext';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import type { LoanApplicationState, JobStatusResponse } from './types/contracts';
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
function toLoanApplication(
  state: LoanApplicationState,
  liveApps?: DashboardApp[]
): LoanApplication {
  const docIds = state.document_ids || [];
  const classified = state.classified_types || {};

  const pageCounts = state.document_pages || {};
  const ocrRoutes = state.ocr_routes || {};
  const filenames = state.document_filenames || {};
  const classMeta = state.classification_metadata || {};
  // A document counts as verified only when at least one finding actually cites
  // it. Hardcoding `verified: true` put a green check on every file in the
  // dossier regardless of whether anything had been checked against it.
  const citedDocIds = new Set(
    (state.findings || []).flatMap((f) =>
      (f.supporting_evidence || []).map((ev) => ev.document_id)
    )
  );

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
      name: filenames[id] || getDocumentTitle(id, docType),
      document_type: mappedType,
      // Undefined rather than a fabricated default: the pane omits the badge
      // until perception reports a real value.
      page_count: pageCounts[id],
      ocr_route: ocrRoutes[id],
      classification: classMeta[id],
      verified: citedDocIds.has(id),
    } as DossierDocument;
  });

  const history = state.status_history || [];
  const liveApp = liveApps?.find((a) => a.application_id === state.application_id);
  const loanAmount = state.loan_amount ?? liveApp?.loan_amount;

  return {
    id: state.application_id,
    applicant_name: state.applicant?.full_name || liveApp?.applicant_name || 'Applicant',
    pan_masked: state.applicant?.pan_number || '—',
    loan_amount: loanAmount,
    currency: 'INR',
    status: state.status,
    // No history yet means no known clock start. `new Date()` here restarted the
    // SLA timer on every 2s poll; undefined lets SlaTimer show "not started".
    created_at: history[0]?.timestamp || liveApp?.created_at,
    updated_at: history.length > 0 ? history[history.length - 1].timestamp : undefined,
    missing_documents: state.missing_documents || [],
    summary_grounded: !!state.summary_grounded,
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
  // Non-dismissable: a dossier we could not refresh must stay visibly stale.
  const [loadError, setLoadError] = useState<string | null>(null);
  const [appsLoading, setAppsLoading] = useState<boolean>(false);
  const [activeJob, setActiveJob] = useState<JobStatusResponse | null>(null);

  // Modal state
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<ReviewDecision | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isNewAppModalOpen, setIsNewAppModalOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [mobilePane, setMobilePane] = useState<'documents' | 'viewer' | 'inspector'>('viewer');
  const [inspectorTab, setInspectorTab] = useState<TabType>('findings');

  const handleOpenCopilot = useCallback(() => {
    setInspectorTab('policy');
    setMobilePane('inspector');
  }, []);

  const { user, isLoading: authLoading } = useAuth();
  const [liveApps, setLiveApps] = useState<DashboardApp[]>([]);
  const [backendError, setBackendError] = useState<string | null>(null);

  const refreshLiveApps = useCallback(async () => {
    setAppsLoading(true);
    try {
      const apps = await api.listApplications();
      if (Array.isArray(apps)) {
        setLiveApps(apps);
        setBackendError(null);
        // Dashboard-first: do NOT auto-pick apps[0]; user opens explicitly.
      }
    } catch (err) {
      // An unreachable backend must be stated, not shown as "no dossiers yet".
      setBackendError(err instanceof Error ? err.message : 'Backend unreachable');
    } finally {
      setAppsLoading(false);
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
  const application = useMemo(() => toLoanApplication(dossierState, liveApps), [dossierState, liveApps]);

  const fetchApplicationData = useCallback(async (isPolling = false) => {
    if (!selectedAppId) return;

    // Offline archetypes are explicit, not a fallback. A live dossier NEVER
    // silently resolves to preset data — showing one applicant's findings under
    // another applicant's id is how a real loan gets signed off on fabricated
    // evidence.
    if (isDemoDossierId(selectedAppId)) {
      const dossier = getDemoDossier(selectedAppId)!;
      setDossierState(dossier);
      setLoadError(null);
      if (dossier.document_ids && dossier.document_ids.length > 0 && !selectedDocId) {
        onSelectDoc(dossier.document_ids[0]);
      }
      if (!isPolling) setNotification(`Demo preset loaded: ${selectedAppId}`);
      return;
    }

    if (!isPolling) setIsLoading(true);
    try {
      const liveState = await api.getApplication(selectedAppId);
      if (!liveState || !liveState.application_id) {
        throw new Error('Backend returned an empty dossier');
      }
      setDossierState(liveState as LoanApplicationState);
      setLoadError(null);
      if (liveState.document_ids && liveState.document_ids.length > 0 && !selectedDocId) {
        onSelectDoc(liveState.document_ids[0]);
      }
      if (!isPolling) {
        setNotification(
          `Live dossier loaded: ${selectedAppId} (${liveState.applicant?.full_name || liveState.applicant_name || 'Underwriting'})`
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch application';
      // Surface the outage instead of substituting data. Polling errors update
      // the banner too, so a backend that dies mid-review is visible.
      setLoadError(msg);
      if (!isPolling) setNotification(msg);
    } finally {
      if (!isPolling) setIsLoading(false);
    }
  }, [selectedAppId, onSelectDoc, selectedDocId]);

  useEffect(() => {
    if (selectedAppId) {
      fetchApplicationData();
    }
  }, [selectedAppId, fetchApplicationData]);

  // Live polling while a job is in flight. 3s keeps us inside
  // MAX_STATUS_POLLS_PER_MIN (30) for the rate-limited /jobs endpoint.
  useEffect(() => {
    const isQueuedOrProcessing = dossierState.status === 'QUEUED' || dossierState.status === 'PROCESSING';
    if (!isQueuedOrProcessing) return;

    const interval = setInterval(() => {
      fetchApplicationData(true);
      refreshLiveApps();
    }, 3000);

    return () => clearInterval(interval);
  }, [dossierState.status, fetchApplicationData, refreshLiveApps]);

  // Job-status polling: the application row alone cannot distinguish "still
  // working" from "the worker died", so poll the authoritative JobModel and
  // surface attempt count + error_message.
  useEffect(() => {
    if (!activeJob) return;
    if (activeJob.status !== 'QUEUED' && activeJob.status !== 'PROCESSING') return;

    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const status = await api.getJobStatus(activeJob.job_id);
        if (cancelled) return;
        setActiveJob(status);
        if (status.status === 'FAILED' || status.status === 'CANCELLED') {
          setNotification(
            `Job ${status.job_id} ${status.status.toLowerCase()}${
              status.error_message ? `: ${status.error_message}` : ''
            }`
          );
          fetchApplicationData(true);
        }
      } catch {
        // Transient poll failure: the dossier poll above is the safety net.
      }
    }, 3000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeJob, fetchApplicationData]);

  // Dropping a dossier drops its job tracking with it.
  useEffect(() => {
    setActiveJob(null);
    setLoadError(null);
  }, [selectedAppId]);

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

  const handleSubmitReview = async (notes: string, confirmAppId: string) => {
    if (!reviewDecision) return;
    setIsSubmitting(true);
    try {
      // Offline archetypes are local by definition: mutate the preset and say so.
      if (isDemoDossierId(selectedAppId)) {
        setDossierState((prev) => ({
          ...prev,
          status: reviewDecision === 'NEEDS_INFO' ? 'NEEDS_INFORMATION' : 'REVIEWED',
          reviewer_decision: reviewDecision,
          reviewer_notes: notes,
        }));
        setNotification(`Preset dossier marked ${reviewDecision} locally — not persisted.`);
        setReviewDecision(null);
        return;
      }

      // Live dossier: a failure here is a failure, full stop. Faking a local
      // REVIEWED state told the underwriter a rejected 409/400/401 had been
      // recorded in the audit trail when nothing was written.
      await api.submitReview(selectedAppId, {
        decision: reviewDecision,
        reviewer_id: user?.email || 'underwriter',
        notes,
        // Server re-checks the dossier-ID challenge; client-side friction alone
        // is bypassable from the console.
        confirm_app_id: confirmAppId,
        corrections: [],
      });
      await fetchApplicationData();
      refreshLiveApps();
      setNotification(`Review submitted: ${reviewDecision} (persisted to PostgreSQL)`);
      setReviewDecision(null);
    } catch (err) {
      // Re-thrown so the modal stays open and renders the reason inline.
      const msg = err instanceof Error ? err.message : 'Error submitting review';
      setNotification(msg);
      throw err;
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

  const handleReclassifyDocument = async (docId: string, newType: string) => {
    try {
      await api.reclassifyDocument(selectedAppId, docId, newType);
      setNotification(`Document ${docId} reclassified as ${newType.replace('_', ' ')}.`);
      await fetchApplicationData();
      refreshLiveApps();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to reclassify document';
      setNotification(msg);
      throw err;
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    try {
      await api.deleteDocument(selectedAppId, docId);
      setNotification(`Document ${docId} removed from dossier.`);
      if (selectedDocId === docId) {
        onSelectDoc('');
      }
      await fetchApplicationData();
      refreshLiveApps();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete document';
      setNotification(msg);
      throw err;
    }
  };

  const handleProcessDossier = async () => {
    setIsProcessing(true);
    try {
      const res = await api.processApplication(selectedAppId);
      // Track the job itself, so a worker-side failure surfaces as an error with
      // a reason instead of an endless "processing" spinner.
      setActiveJob({
        job_id: res.job_id,
        application_id: res.application_id,
        status: res.status,
        attempt_count: 1,
      });
      setNotification(`Pipeline enqueued for ${selectedAppId} (Job: ${res.job_id}).`);
      await fetchApplicationData();
      refreshLiveApps();
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Failed to trigger pipeline');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancelJob = useCallback(async () => {
    if (!activeJob) return;
    try {
      await api.cancelJob(activeJob.job_id);
      setNotification(`Job ${activeJob.job_id} cancelled.`);
      setActiveJob(null);
      await fetchApplicationData();
      refreshLiveApps();
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Failed to cancel job');
    }
  }, [activeJob, fetchApplicationData, refreshLiveApps]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Global shortcut: Ctrl+K / Cmd+K opens Underwriter Copilot
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        handleOpenCopilot();
        return;
      }

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

  const isDemoPreset = isDemoDossierId(selectedAppId);
  const flagCount = (dossierState.findings || []).filter((f) => f.verdict === 'flag').length;
  // Guard empty app/doc: the viewer fetches through the authenticated API
  // client, and falls through to the `unavailable` empty state rather than
  // pdf.js MissingPDF. Demo archetypes have no backend document route, so
  // leaving this undefined lets the viewer generate the synthetic preset PDF.
  const pdfSource = useMemo(
    () =>
      !isDemoPreset && selectedAppId && selectedDocId
        ? { applicationId: selectedAppId, documentId: selectedDocId }
        : undefined,
    [isDemoPreset, selectedAppId, selectedDocId]
  );

  // Real loan-app start: dashboard first when no dossier selected.
  if (!selectedAppId) {
    // Signed out is signed out in both modes. Gating this on google-only left
    // mock-mode Logout as a dead end with no way back in short of a reload.
    if (!user && !authLoading) {
      return <LoginPage onLoggedIn={() => refreshLiveApps()} />;
    }
    return (
      <div className="h-screen w-screen flex flex-col bg-theme-app overflow-y-auto">
        {authLoading ? (
          <div className="m-auto text-xs text-theme-muted">Verifying session…</div>
        ) : (
          <DashboardPage
            apps={liveApps}
            isLoading={appsLoading}
            backendError={backendError}
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
        reviewerDecision={application.reviewer_decision}
        createdAt={application.created_at}
        updatedAt={application.updated_at}
        onOpenShortcuts={() => setShortcutsOpen(true)}
        onOpenCopilot={handleOpenCopilot}
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

      {/* Stale-dossier banner: stays until a refresh succeeds, because acting on
          a dossier we could not re-read is the risk we are guarding against. */}
      {loadError && (
        <div
          role="alert"
          className="bg-theme-flag-bg border-b border-theme-flag-border text-theme-flag text-[11px] font-mono px-4 py-1.5 flex items-center justify-between gap-3 shrink-0"
        >
          <span className="truncate">
            Dossier not refreshed — showing last known state. {loadError}
          </span>
          <button
            type="button"
            onClick={() => fetchApplicationData()}
            className="shrink-0 px-2 py-0.5 rounded-xs border border-theme-flag-border hover:bg-theme-card"
          >
            Retry
          </button>
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

      {/* Elevated Pipeline Action Banner: Appears on UPLOADED, or when re-run is warranted (NEEDS_INFO, FAILED) */}
      {(application.status === 'UPLOADED' || application.status === 'NEEDS_INFORMATION' || application.status === 'FAILED') && (
        <div className={`border-b px-4 py-2 flex items-center justify-between gap-3 shrink-0 ${
          application.status === 'FAILED'
            ? 'bg-rose-50 border-rose-200'
            : application.status === 'NEEDS_INFORMATION'
            ? 'bg-amber-50 border-amber-200'
            : 'bg-theme-brand/10 border-theme-brand/30'
        }`}>
          <div className="flex items-center gap-2 text-xs">
            <span className={`w-2 h-2 rounded-full shrink-0 ${
              application.status === 'FAILED'
                ? 'bg-rose-600'
                : application.status === 'NEEDS_INFORMATION'
                ? 'bg-amber-600 animate-pulse'
                : 'bg-theme-brand animate-pulse'
            }`} />
            <span className="font-mono font-bold text-theme-primary">
              {application.status === 'UPLOADED'
                ? `Dossier Ingested (${application.documents.length} ${application.documents.length === 1 ? 'document' : 'documents'})`
                : application.status === 'NEEDS_INFORMATION'
                ? `Supplemental Information Requested (${application.documents.length} ${application.documents.length === 1 ? 'document' : 'documents'})`
                : 'Pipeline Execution Halted'}
            </span>
            <span className="text-theme-secondary hidden sm:inline">
              {application.status === 'UPLOADED'
                ? '· Ready for OCR perception, fact extraction, and deterministic credit rules.'
                : application.status === 'NEEDS_INFORMATION'
                ? '· New documents uploaded? Run pipeline to re-verify applicant dossier.'
                : '· Re-run pipeline to retry perception and deterministic rules.'}
            </span>
          </div>
          <button
            type="button"
            disabled={isProcessing || isDemoPreset || application.documents.length === 0}
            onClick={handleProcessDossier}
            className="px-3 py-1.5 rounded-xs bg-theme-brand hover:opacity-90 text-white text-xs font-mono font-bold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
            title={
              application.documents.length === 0
                ? 'Upload at least one document first'
                : 'Execute deterministic credit verification pipeline'
            }
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Running Pipeline…</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{application.status === 'UPLOADED' ? 'Run Verification Pipeline' : 'Re-run Pipeline'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      )}

      {/* Main Workspace: 3-pane layout on desktop, tabbed on mobile/tablet.
          Previously this hardcoded `lg:grid lg:grid-cols-[280px_1fr_390px]`,
          which broke on smaller laptops (e.g. 1024-1280px) and completely
          removed the entire review workflow on anything narrower than a laptop. */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Pane: Dossier Documents */}
        <div className={`${mobilePane === 'documents' ? 'flex' : 'hidden'} lg:block shrink-0 w-full lg:w-auto`}>
          <LeftDossierPane
            application={application}
            activeDocId={selectedDocId}
            onSelectDocId={(docId) => {
              handleSelectDoc(docId);
              setMobilePane('viewer');
            }}
            onUploadDocument={handleUploadDocument}
            onReclassifyDocument={handleReclassifyDocument}
            onDeleteDocument={handleDeleteDocument}
            isReadOnlyPreset={isDemoPreset}
            width={280}
          />
        </div>

        {/* Center Pane: PDF.js Viewer */}
        <div className={`${mobilePane === 'viewer' ? 'block' : 'hidden'} lg:block flex-1 h-full min-w-0 relative`}>
          <PdfViewer
            docId={selectedDocId}
            docTitle={currentDocTitle}
            pdfSource={pdfSource}
            isDemoMode={isDemoPreset}
          />

          {/* Quick Floating AI Button (Visible in Center/Viewer pane when Q&A isn't active) */}
          {inspectorTab !== 'policy' && (
            <button
              type="button"
              onClick={handleOpenCopilot}
              className="absolute bottom-4 right-4 z-20 flex items-center gap-2 px-3 py-2 rounded-full bg-theme-brand text-white shadow-lg hover:shadow-xl hover:scale-105 transition-all text-xs font-mono font-bold group"
              title="Ask AI (Ctrl+K)"
            >
              <Sparkles className="w-4 h-4 group-hover:rotate-12 transition-transform" />
              <span>Ask AI</span>
              <kbd className="text-[10px] bg-white/20 px-1.5 py-0.5 rounded text-white/90">^K</kbd>
            </button>
          )}
        </div>

        {/* Right Pane: Inspector */}
        <div className={`${mobilePane === 'inspector' ? 'block' : 'hidden'} lg:block shrink-0 h-full min-h-0 w-full lg:w-auto`}>
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
            activeJob={activeJob}
            onCancelJob={handleCancelJob}
            isReadOnlyPreset={isDemoPreset}
            width={390}
            activeTab={inspectorTab}
            onTabChange={setInspectorTab}
          />
        </div>
      </div>

      {/* Mobile/tablet pane switcher */}
      <nav className="lg:hidden border-t border-theme-border bg-theme-panel grid grid-cols-3 shrink-0">
        {([
          ['documents', `Documents (${application.documents.length})`],
          ['viewer', 'Viewer'],
          ['inspector', `Inspector${flagCount > 0 ? ` (${flagCount})` : ''}`],
        ] as const).map(([pane, label]) => (
          <button
            key={pane}
            type="button"
            onClick={() => setMobilePane(pane)}
            aria-current={mobilePane === pane}
            className={`py-2.5 text-[11px] font-mono font-bold border-r border-theme-border last:border-r-0 transition-colors ${
              mobilePane === pane
                ? 'bg-theme-card text-theme-primary'
                : 'text-theme-muted hover:text-theme-primary'
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

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
