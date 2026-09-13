import React, { useState } from 'react';
import { LoanApplication } from '../../types/application';
import { EvidenceRef } from '../../types/evidence';
import { ReviewDecision } from '../../types/api';
import { JobStatusResponse } from '../../types/contracts';
import { FindingCard } from '../review/FindingCard';
import { FactsTab } from '../review/FactsTab';
import { MemoNarrativeTab } from '../review/MemoNarrativeTab';
import { PolicyQaTab } from '../review/PolicyQaTab';
import { AuditTrailTab } from '../review/AuditTrailTab';
import { getEvidenceKey } from '../../utils/coordinates';
import {
  ShieldCheck,
  Table,
  FileText,
  BookOpen,
  History,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  Play,
  Loader2,
  XCircle,
  FileWarning,
} from 'lucide-react';

interface RightInspectorPaneProps {
  application: LoanApplication;
  activeEvidenceKey: string | null;
  focusedFindingIndex: number;
  onSelectFindingIndex: (idx: number) => void;
  onSelectEvidence: (ev: EvidenceRef, ruleId?: string) => void;
  onTriggerAction: (decision: ReviewDecision) => void;
  onProcessDossier?: () => Promise<void>;
  isProcessing?: boolean;
  inspectedKeys?: Set<string>;
  activeJob?: JobStatusResponse | null;
  onCancelJob?: () => void;
  isReadOnlyPreset?: boolean;
  width: number;
  activeTab?: TabType;
  onTabChange?: (tab: TabType) => void;
}

export type TabType = 'findings' | 'facts' | 'cam' | 'policy' | 'audit';

const REQUIRED_DOC_LABELS: Record<string, string> = {
  application_form: 'Application Form',
  payslip: 'Payslip',
  bank_statement: 'Bank Statement',
  tax_acknowledgement: 'Tax Acknowledgement (ITR-V)',
  id_card: 'KYC / ID Proof',
};

export const RightInspectorPane: React.FC<RightInspectorPaneProps> = ({
  application,
  activeEvidenceKey,
  focusedFindingIndex,
  onSelectFindingIndex,
  onSelectEvidence,
  onTriggerAction,
  onProcessDossier,
  isProcessing = false,
  inspectedKeys,
  activeJob,
  onCancelJob,
  isReadOnlyPreset = false,
  width,
  activeTab: controlledActiveTab,
  onTabChange,
}) => {
  const [internalActiveTab, setInternalActiveTab] = useState<TabType>('findings');
  const activeTab = controlledActiveTab ?? internalActiveTab;
  const setActiveTab = (tab: TabType) => {
    if (onTabChange) {
      onTabChange(tab);
    } else {
      setInternalActiveTab(tab);
    }
  };

  const flagCount = application.findings.filter((f) => f.verdict === 'flag').length;
  const passCount = application.findings.filter((f) => f.verdict === 'pass').length;
  const unknownCount = application.findings.filter((f) => f.verdict === 'unknown').length;
  const missingDocuments = application.missing_documents || [];

  // Flagged findings the reviewer has not yet opened the evidence for. This is
  // the signal `inspectedKeys` was always collected for but never displayed.
  const uninspectedFlags = application.findings.filter(
    (f) =>
      f.verdict === 'flag' &&
      !(f.supporting_evidence || []).some((ev) => inspectedKeys?.has(getEvidenceKey(ev)))
  ).length;
  // Sign-off unlocks ONLY on a reviewed-ready dossier with findings present.
  // Backend enforces the same (409 unless READY_FOR_REVIEW); this mirrors it
  // so the underwriter can never authorize from UPLOADED/QUEUED/PROCESSING
  // or sign an empty dossier.
  const canSignOff =
    application.status === 'READY_FOR_REVIEW' && application.findings.length > 0;
  const isActionDisabled = !canSignOff;
  const readyToSign = flagCount === 0 && unknownCount === 0 && application.findings.length > 0;

  return (
    <aside
      style={{ width: `${width}px` }}
      className="h-full min-h-0 flex-none flex flex-col border-l border-theme-border bg-theme-panel overflow-hidden transition-colors duration-200"
    >
      {/* Tab Navigation Header.
          Labels are deliberately short: with five tabs, full labels ("Audit
          Findings", "Facts Ledger", "Policy RAG") overflowed the 390px pane and
          pushed Policy and Audit off-screen with no visible scroll affordance,
          so two tabs were unreachable at 1280px. Short labels fit; overflow-x
          stays as a safety net for narrower panes. */}
      <div className="h-11 min-h-[44px] border-b border-theme-border bg-theme-header px-1.5 flex items-center overflow-x-auto">
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={() => setActiveTab('findings')}
            className={`flex items-center gap-1 px-1.5 py-1.5 rounded-xs text-[11px] font-mono font-bold transition-all whitespace-nowrap ${
              activeTab === 'findings'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-theme-brand" />
            <span>Findings</span>
            {flagCount > 0 && (
              <span className="ml-0.5 px-1 py-0.5 rounded-full text-[10px] font-mono font-bold bg-theme-flag-bg text-theme-flag border border-theme-flag-border">
                {flagCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('facts')}
            className={`flex items-center gap-1 px-1.5 py-1.5 rounded-xs text-[11px] font-mono font-bold transition-all whitespace-nowrap ${
              activeTab === 'facts'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <Table className="w-3.5 h-3.5 text-theme-secondary" />
            <span>Facts</span>
          </button>

          <button
            onClick={() => setActiveTab('cam')}
            className={`flex items-center gap-1 px-1.5 py-1.5 rounded-xs text-[11px] font-mono font-bold transition-all whitespace-nowrap ${
              activeTab === 'cam'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-theme-secondary" />
            <span>CAM</span>
          </button>

          <button
            onClick={() => setActiveTab('policy')}
            className={`flex items-center gap-1 px-1.5 py-1.5 rounded-xs text-[11px] font-mono font-bold transition-all whitespace-nowrap ${
              activeTab === 'policy'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5 text-theme-secondary" />
            <span>Q&amp;A</span>
            {flagCount > 0 && (
              <span className="ml-0.5 px-1 py-0.5 rounded-full text-[10px] font-mono font-bold bg-theme-flag-bg text-theme-flag border border-theme-flag-border">
                {flagCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-1 px-1.5 py-1.5 rounded-xs text-[11px] font-mono font-bold transition-all whitespace-nowrap ${
              activeTab === 'audit'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <History className="w-3.5 h-3.5 text-theme-secondary" />
            <span>Audit</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div
        className={`flex-1 min-h-0 bg-theme-card ${
          activeTab === 'policy'
            ? 'overflow-hidden flex flex-col p-0'
            : 'overflow-y-auto p-3.5'
        }`}
      >
        {activeTab === 'findings' && (
          <div className="space-y-3">
            {/* Terminal failure: the dossier stopped, and the reason is shown.
                Previously a failed job left the card spinning forever. */}
            {application.status === 'FAILED' && (
              <div className="p-3.5 rounded-xs bg-theme-flag-bg border border-theme-flag-border space-y-2">
                <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-theme-flag">
                  <XCircle className="w-4 h-4" />
                  <span>Pipeline Failed</span>
                </div>
                <p className="text-[11px] text-theme-secondary leading-relaxed">
                  {activeJob?.error_message ||
                    'The verification pipeline could not complete. Check worker logs, then re-upload or retry.'}
                </p>
                {activeJob && (
                  <p className="text-[10px] font-mono text-theme-muted">
                    Job {activeJob.job_id} · attempt {activeJob.attempt_count}
                  </p>
                )}
              </div>
            )}

            {application.status === 'CANCELLED' && (
              <div className="p-3.5 rounded-xs bg-theme-panel border border-theme-border space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-theme-secondary">
                  <XCircle className="w-4 h-4" />
                  <span>Processing Cancelled</span>
                </div>
                <p className="text-[11px] text-theme-secondary leading-relaxed">
                  This dossier's verification job was cancelled. Create a new dossier to run it again.
                </p>
              </div>
            )}

            {/* Pipeline Trigger Card for newly uploaded or processing applications */}
            {(application.status === 'UPLOADED' || application.status === 'QUEUED' || application.status === 'PROCESSING') && (
              <div className="p-3.5 rounded-xs bg-theme-unknown-bg border border-theme-unknown-border space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-theme-unknown">
                    Dossier Processing Pipeline
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-xs bg-theme-card border border-theme-unknown-border text-theme-unknown shrink-0">
                    {application.status}
                  </span>
                </div>
                <p className="text-[11px] text-theme-secondary leading-relaxed">
                  {application.status === 'UPLOADED'
                    ? 'Documents have been uploaded. Trigger OCR perception, fact extraction, and deterministic credit rules.'
                    : 'Pipeline execution in progress. Orchestrating OCR routing, entity extraction, and policy retrieval...'}
                </p>
                {application.status === 'UPLOADED' && onProcessDossier && (
                  <button
                    type="button"
                    disabled={isProcessing || isReadOnlyPreset || application.documents.length === 0}
                    onClick={() => onProcessDossier()}
                    title={
                      isReadOnlyPreset
                        ? 'Offline preset — nothing to process on the backend'
                        : application.documents.length === 0
                          ? 'Upload at least one document first'
                          : 'Run the deterministic verification pipeline'
                    }
                    className="w-full py-2 px-3 rounded-xs text-xs font-mono font-bold bg-theme-unknown hover:opacity-90 text-white flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Enqueuing Verification Job...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        <span>Run FinScan Verification Pipeline</span>
                      </>
                    )}
                  </button>
                )}
                {(application.status === 'QUEUED' || application.status === 'PROCESSING') && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center gap-2 text-xs font-mono text-theme-unknown">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Worker processing pipeline…</span>
                    </div>
                    {activeJob && (
                      <p className="text-[10px] font-mono text-theme-muted">
                        Job {activeJob.job_id} · status {activeJob.status} · attempt{' '}
                        {activeJob.attempt_count}
                      </p>
                    )}
                    {onCancelJob && activeJob && (
                      <button
                        type="button"
                        onClick={onCancelJob}
                        className="w-full py-1.5 px-3 rounded-xs text-[11px] font-mono font-bold bg-theme-card hover:bg-theme-panel text-theme-secondary hover:text-theme-primary border border-theme-border transition-colors cursor-pointer"
                      >
                        Cancel job
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Missing required documents: computed by the pipeline and, until
                now, never shown to the person accountable for the decision. */}
            {missingDocuments.length > 0 && (
              <div className="p-3 rounded-xs bg-theme-unknown-bg border border-theme-unknown-border space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-theme-unknown">
                  <FileWarning className="w-3.5 h-3.5" />
                  <span>Missing Documents ({missingDocuments.length})</span>
                </div>
                <ul className="text-[11px] text-theme-secondary space-y-0.5">
                  {missingDocuments.map((doc) => (
                    <li key={doc} className="flex items-center gap-1.5">
                      <span className="text-theme-unknown select-none">•</span>
                      <span>{REQUIRED_DOC_LABELS[doc] || doc.replace(/_/g, ' ')}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Decision summary: answers "can I sign this?" in seconds */}
            <div className="p-3 rounded-xs bg-theme-panel border border-theme-border shadow-2xs">
              <div className="flex items-center gap-2 text-xs font-mono font-bold">
                <span className="text-theme-pass">{passCount} pass</span>
                <span className="text-theme-muted">·</span>
                <span className={flagCount > 0 ? 'text-theme-flag' : 'text-theme-muted'}>
                  {flagCount} flag
                </span>
                <span className="text-theme-muted">·</span>
                <span className={unknownCount > 0 ? 'text-theme-unknown' : 'text-theme-muted'}>
                  {unknownCount} unknown
                </span>
              </div>
              <p className="text-[11px] text-theme-secondary mt-1 leading-relaxed">
                {application.status === 'REVIEWED'
                  ? `Decision recorded${application.reviewer_decision ? `: ${application.reviewer_decision}` : ''}. Thread sealed.`
                  : readyToSign
                    ? 'All checks verified. Ready for underwriter sign-off below.'
                    : 'Resolve flagged items or request information before signing.'}
              </p>
              {uninspectedFlags > 0 && (
                <p className="text-[10px] text-theme-flag font-mono mt-1">
                  {uninspectedFlags} flagged {uninspectedFlags === 1 ? 'finding has' : 'findings have'} unopened
                  evidence — press Enter or click a citation to review.
                </p>
              )}
              {application.updated_at && (
                <p className="text-[10px] text-theme-muted font-mono mt-1">
                  State as of {new Date(application.updated_at).toLocaleString()}
                </p>
              )}
            </div>

            <div className="flex items-center justify-between pb-2 border-b border-theme-border">
              <span className="text-xs font-serif font-bold text-theme-primary">
                Deterministic Audit Invariants ({application.findings.length})
              </span>
              {application.findings.length > 0 && (
                <span className="text-[10px] text-theme-muted font-mono">Navigate: J / K</span>
              )}
            </div>

            {application.findings.length === 0 ? (
              <div className="p-6 text-center border border-dashed border-theme-border rounded-xs bg-theme-panel/30">
                <ShieldCheck className="w-8 h-8 text-theme-muted mx-auto mb-2 opacity-50" />
                <p className="text-xs font-serif font-bold text-theme-primary mb-1">
                  No Audit Invariants Evaluated Yet
                </p>
                <p className="text-[11px] text-theme-muted leading-relaxed">
                  {application.documents.length === 0
                    ? 'Upload applicant documents to enable deterministic rules evaluation.'
                    : 'Click "Run FinScan Verification Pipeline" above to execute deterministic audit rules.'}
                </p>
              </div>
            ) : (
              application.findings.map((finding, idx) => (
                <FindingCard
                  key={finding.rule_id}
                  finding={finding}
                  isFocused={focusedFindingIndex === idx}
                  onSelectFinding={() => onSelectFindingIndex(idx)}
                  onSelectEvidence={onSelectEvidence}
                  activeEvidenceKey={activeEvidenceKey}
                />
              ))
            )}
          </div>
        )}

        {activeTab === 'facts' && (
          <FactsTab application={application} onSelectEvidence={onSelectEvidence} />
        )}

        {activeTab === 'cam' && (
          <MemoNarrativeTab application={application} isReadOnlyPreset={isReadOnlyPreset} />
        )}

        {activeTab === 'policy' && (
          <PolicyQaTab
            applicationId={application.id}
            onSelectEvidence={onSelectEvidence}
            isReadOnlyPreset={isReadOnlyPreset}
            flaggedFindings={application.findings.filter((f) => f.verdict === 'flag')}
          />
        )}

        {activeTab === 'audit' && (
          <AuditTrailTab applicationId={application.id} isReadOnlyPreset={isReadOnlyPreset} />
        )}
      </div>

      {/* Sticky Bottom HITL Underwriter Sign-Off Footer */}
      <div className="border-t border-theme-border bg-theme-panel p-3.5 space-y-2.5 z-20 flex-none shadow-xs">
        {application.status === 'REVIEWED' ? (
          <div className="p-3 rounded-xs bg-theme-pass-bg border border-theme-pass-border text-xs text-theme-pass flex items-center justify-between font-mono font-bold">
            <span className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-theme-pass" />
              <span>Dossier Decision Recorded: {application.reviewer_decision || 'APPROVED'}</span>
            </span>
            <span className="text-[10px] text-theme-muted font-normal">Thread Sealed</span>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between text-[11px] text-theme-secondary">
              <span className="font-mono font-bold text-theme-primary uppercase tracking-wider">
                Underwriter Sign-Off
              </span>
              <span className="font-mono text-[10px] text-theme-muted">Hotkeys: [A] [R] [N]</span>
            </div>

            {!canSignOff && (
              <p className="text-[10px] font-mono text-theme-unknown leading-relaxed">
                Sign-off unlocks when the pipeline reaches READY_FOR_REVIEW with findings present.
              </p>
            )}

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('APPROVED')}
                className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xs text-xs font-mono font-bold bg-theme-pass hover:opacity-90 text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
                title="Approve Loan Application (A)"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Approve</span>
              </button>

              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('REJECTED')}
                className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xs text-xs font-mono font-bold bg-theme-flag hover:opacity-90 text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
                title="Reject Loan Application (R)"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Reject</span>
              </button>

              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('NEEDS_INFO')}
                className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xs text-xs font-mono font-bold bg-theme-unknown hover:opacity-90 text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
                title="Request Supplemental Information (N)"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Need Info</span>
              </button>
            </div>
          </>
        )}
      </div>
    </aside>
  );
};
