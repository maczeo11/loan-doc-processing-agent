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
  onSelectEvidence: (ev: EvidenceRef) => void;
  onTriggerAction: (decision: ReviewDecision) => void;
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
  const isActionDisabled = application.status === 'REVIEWED';

  return (
    <aside
      style={{ width: `${width}px` }}
      className="h-full flex-none flex flex-col border-l border-[#E3DDD3] bg-[#FBF9F5] select-none overflow-hidden"
    >
      {/* Tab Navigation Header */}
      <div className="h-11 min-h-[44px] border-b border-[#E3DDD3] bg-[#F2EDE4] px-2.5 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setActiveTab('findings')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-mono font-bold transition-all ${
              activeTab === 'findings'
                ? 'bg-white text-stone-900 border border-[#D5CFC5] shadow-xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-white/60'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-stone-700" />
            <span>Audit Findings</span>
            {flagCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-rose-100 text-rose-800 border border-rose-300">
                {flagCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('facts')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-mono font-bold transition-all ${
              activeTab === 'facts'
                ? 'bg-white text-stone-900 border border-[#D5CFC5] shadow-xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-white/60'
            }`}
          >
            <Table className="w-3.5 h-3.5 text-stone-700" />
            <span>Facts Ledger</span>
          </button>

          <button
            onClick={() => setActiveTab('cam')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-mono font-bold transition-all ${
              activeTab === 'cam'
                ? 'bg-white text-stone-900 border border-[#D5CFC5] shadow-xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-white/60'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-stone-700" />
            <span>CAM Memo</span>
          </button>

          <button
            onClick={() => setActiveTab('policy')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-mono font-bold transition-all ${
              activeTab === 'policy'
                ? 'bg-white text-stone-900 border border-[#D5CFC5] shadow-xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-white/60'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5 text-stone-700" />
            <span>Policy RAG</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-3.5 bg-white">
        {activeTab === 'findings' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#E3DDD3]">
              <span className="text-xs font-serif font-bold text-stone-800">
                Deterministic Audit Invariants ({application.findings.length})
              </span>
              <span className="text-[10px] text-stone-500 font-mono">Navigate: J / K</span>
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

        {activeTab === 'facts' && <FactsTab application={application} onSelectEvidence={onSelectEvidence} />}

        {activeTab === 'cam' && <MemoNarrativeTab application={application} />}

        {activeTab === 'policy' && <PolicyQaTab applicationId={application.id} onSelectEvidence={onSelectEvidence} />}
      </div>

      {/* Sticky Bottom HITL Underwriter Sign-Off Footer */}
      <div className="border-t border-[#E3DDD3] bg-[#F8F6F1] p-3.5 space-y-2.5 z-20 flex-none shadow-xs">
        {application.status === 'REVIEWED' ? (
          <div className="p-3 rounded-sm bg-[#ECFDF5] border border-[#A7F3D0] text-xs text-[#065F46] flex items-center justify-between font-mono font-bold">
            <span className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-[#059669]" />
              <span>Dossier Decision Recorded: {application.reviewer_decision || 'APPROVED'}</span>
            </span>
            <span className="text-[10px] text-stone-500 font-normal">Thread Sealed</span>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between text-[11px] text-stone-600">
              <span className="font-mono font-bold text-stone-800 uppercase tracking-wider">
                Underwriter Sign-Off
              </span>
              <span className="font-mono text-[10px] text-stone-500">Shortcuts: [A] [R] [N]</span>
            </div>

            <div className="grid grid-cols-3 gap-2.5">
              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('APPROVED')}
                className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-sm text-xs font-mono font-bold bg-[#14532D] hover:bg-[#166534] text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
                title="Approve Loan Application (A)"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Approve</span>
              </button>

              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('REJECTED')}
                className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-sm text-xs font-mono font-bold bg-[#991B1B] hover:bg-[#7F1D1D] text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
                title="Reject Loan Application (R)"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Reject</span>
              </button>

              <button
                type="button"
                disabled={isActionDisabled}
                onClick={() => onTriggerAction('NEEDS_INFO')}
                className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-sm text-xs font-mono font-bold bg-[#B45309] hover:bg-[#92400E] text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
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
