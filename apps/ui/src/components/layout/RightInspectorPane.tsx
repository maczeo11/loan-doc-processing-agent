import React, { useState } from 'react';
import { LoanApplication } from '../../types/application';
import { EvidenceRef } from '../../types/evidence';
import { ReviewDecision } from '../../types/api';
import { FindingCard } from '../review/FindingCard';
import { FactsTab } from '../review/FactsTab';
import { MemoNarrativeTab } from '../review/MemoNarrativeTab';
import { PolicyQaTab } from '../review/PolicyQaTab';
import { ShieldCheck, Table, FileText, BookOpen, CheckCircle, AlertTriangle, HelpCircle } from 'lucide-react';

interface RightInspectorPaneProps {
  application: LoanApplication;
  activeEvidenceKey: string | null;
  focusedFindingIndex: number;
  onSelectFindingIndex: (idx: number) => void;
  onSelectEvidence: (ev: EvidenceRef, ruleId?: string) => void;
  onTriggerAction: (decision: ReviewDecision) => void;
  inspectedKeys?: Set<string>;
  width: number;
}

type TabType = 'findings' | 'facts' | 'cam' | 'policy';

export const RightInspectorPane: React.FC<RightInspectorPaneProps> = ({
  application,
  activeEvidenceKey,
  focusedFindingIndex,
  onSelectFindingIndex,
  onSelectEvidence,
  onTriggerAction,
  width,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('findings');

  const flagCount = application.findings.filter((f) => f.verdict === 'flag').length;
  const passCount = application.findings.filter((f) => f.verdict === 'pass').length;
  const unknownCount = application.findings.filter((f) => f.verdict === 'unknown').length;
  const isActionDisabled = application.status === 'REVIEWED';
  const readyToSign = flagCount === 0 && unknownCount === 0 && application.findings.length > 0;

  return (
    <aside
      style={{ width: `${width}px` }}
      className="h-full flex-none flex flex-col border-l border-theme-border bg-theme-panel select-none overflow-hidden transition-colors duration-200"
    >
      {/* Tab Navigation Header */}
      <div className="h-11 min-h-[44px] border-b border-theme-border bg-theme-header px-2 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('findings')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs text-xs font-mono font-bold transition-all ${
              activeTab === 'findings'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-theme-brand" />
            <span>Audit Findings</span>
            {flagCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-theme-flag-bg text-theme-flag border border-theme-flag-border">
                {flagCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('facts')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs text-xs font-mono font-bold transition-all ${
              activeTab === 'facts'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <Table className="w-3.5 h-3.5 text-theme-secondary" />
            <span>Facts Ledger</span>
          </button>

          <button
            onClick={() => setActiveTab('cam')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs text-xs font-mono font-bold transition-all ${
              activeTab === 'cam'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-theme-secondary" />
            <span>CAM Memo</span>
          </button>

          <button
            onClick={() => setActiveTab('policy')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs text-xs font-mono font-bold transition-all ${
              activeTab === 'policy'
                ? 'bg-theme-card text-theme-primary border border-theme-border shadow-xs'
                : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5 text-theme-secondary" />
            <span>Policy RAG</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-3.5 bg-theme-card">
        {activeTab === 'findings' && (
          <div className="space-y-3">
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
              <span className="text-[10px] text-theme-muted font-mono">Navigate: J / K</span>
            </div>

            {application.findings.map((finding, idx) => (
              <FindingCard
                key={finding.rule_id}
                finding={finding}
                isFocused={focusedFindingIndex === idx}
                onSelectFinding={() => onSelectFindingIndex(idx)}
                onSelectEvidence={onSelectEvidence}
                activeEvidenceKey={activeEvidenceKey}
              />
            ))}
          </div>
        )}

        {activeTab === 'facts' && (
          <FactsTab application={application} onSelectEvidence={onSelectEvidence} />
        )}

        {activeTab === 'cam' && <MemoNarrativeTab application={application} />}

        {activeTab === 'policy' && (
          <PolicyQaTab applicationId={application.id} onSelectEvidence={onSelectEvidence} />
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

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('APPROVED')}
                className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xs text-xs font-mono font-bold bg-emerald-700 hover:bg-emerald-600 text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
                title="Approve Loan Application (A)"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Approve</span>
              </button>

              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('REJECTED')}
                className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xs text-xs font-mono font-bold bg-rose-700 hover:bg-rose-600 text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
                title="Reject Loan Application (R)"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Reject</span>
              </button>

              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('NEEDS_INFO')}
                className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xs text-xs font-mono font-bold bg-amber-700 hover:bg-amber-600 text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
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
