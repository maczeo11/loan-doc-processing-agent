import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ShieldCheck,
  FileCheck2,
  TrendingUp,
  UserCheck,
  FileText,
  ThumbsUp,
  ThumbsDown,
  Info,
  ChevronRight,
} from 'lucide-react';
import type {
  Finding,
  RuleVerdict,
  LoanApplicationState,
  ReviewDecisionRequest,
} from '../types/contracts';
import { useEvidenceNavigation } from '../context/EvidenceNavigationContext';
import { QaPanel } from './qa/QaPanel';

interface ReviewPaneProps {
  state: LoanApplicationState;
  onSubmitReview?: (decision: ReviewDecisionRequest['decision'], notes: string) => void;
  isDemoMode?: boolean;
}

export const ReviewPane: React.FC<ReviewPaneProps> = ({ state, onSubmitReview, isDemoMode = false }) => {
  const { activeEvidence, navigateToEvidence } = useEvidenceNavigation();
  const [activeTab, setActiveTab] = useState<'findings' | 'facts' | 'cam' | 'qa'>('findings');
  const [reviewerNotes, setReviewerNotes] = useState<string>('');
  const [submittingDecision, setSubmittingDecision] = useState<string | null>(null);

  const [pendingDecision, setPendingDecision] = useState<
    ReviewDecisionRequest['decision'] | null
  >(null);

  const findings = state.findings || [];

  const getVerdictBadge = (verdict: RuleVerdict) => {
    switch (verdict) {
      case 'pass':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            PASS
          </span>
        );
      case 'flag':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
            <AlertTriangle className="w-3 h-3 text-rose-600" />
            FLAG
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
            <HelpCircle className="w-3 h-3 text-amber-600" />
            UNKNOWN
          </span>
        );
    }
  };

  const handleDecisionClick = (decision: ReviewDecisionRequest['decision']) => {
  setPendingDecision(decision);
  };

  const confirmDecision = () => {
    if (!pendingDecision) return;

    setSubmittingDecision(pendingDecision);
    if (onSubmitReview) {
       onSubmitReview(pendingDecision, reviewerNotes);
   }

    setPendingDecision(null);
  };

  return (
    <aside className="relative w-full h-full flex flex-col bg-white border-l border-slate-200">
      {/* Tab Navigation */}
      <div className="flex items-center border-b border-slate-200 bg-slate-50 px-2 pt-2">
        <button
          onClick={() => setActiveTab('findings')}
          className={`flex items-center gap-1.5 px-2.5 py-2 text-xs font-semibold rounded-t-lg border-t border-x transition-colors ${
            activeTab === 'findings'
              ? 'bg-white border-slate-200 text-indigo-600 border-b-transparent'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          Findings ({findings.length})
        </button>
        <button
          onClick={() => setActiveTab('facts')}
          className={`flex items-center gap-1.5 px-2.5 py-2 text-xs font-semibold rounded-t-lg border-t border-x transition-colors ${
            activeTab === 'facts'
              ? 'bg-white border-slate-200 text-indigo-600 border-b-transparent'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5" />
          Facts
        </button>
        <button
          onClick={() => setActiveTab('cam')}
          className={`flex items-center gap-1.5 px-2.5 py-2 text-xs font-semibold rounded-t-lg border-t border-x transition-colors ${
            activeTab === 'cam'
              ? 'bg-white border-slate-200 text-indigo-600 border-b-transparent'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          CAM
        </button>
        <button
          onClick={() => setActiveTab('qa')}
          className={`flex items-center gap-1.5 px-2.5 py-2 text-xs font-semibold rounded-t-lg border-t border-x transition-colors ${
            activeTab === 'qa'
              ? 'bg-white border-slate-200 text-indigo-600 border-b-transparent'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <HelpCircle className="w-3.5 h-3.5" />
          Policy Q&A
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'qa' ? (
        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          <QaPanel applicationId={state.application_id} isDemoMode={isDemoMode} />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {activeTab === 'findings' && (
            <div className="space-y-3">
              <div className="text-[11px] text-slate-500 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                Deterministic financial rules engine evaluated against bank underwriting policy. Every verdict traces back to verified document evidence.
              </div>

            {findings.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs">
                No audit findings available for this dossier.
              </div>
            ) : (
              findings.map((f: Finding) => (
                <div
                  key={f.rule_id}
                  className="p-3 rounded-lg border border-slate-200 bg-white hover:border-slate-300 transition-shadow shadow-xs space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                        {f.rule_id}
                      </span>
                      <h4 className="text-xs font-bold text-slate-900 mt-1">
                        {f.rule_name}
                      </h4>
                    </div>
                    {getVerdictBadge(f.verdict)}
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {f.reason}
                  </p>
                  {f.supporting_evidence && f.supporting_evidence.length > 0 && (
                    <div className="pt-1 flex flex-wrap gap-1.5">
                      {f.supporting_evidence.map((ev, idx) => {
                        const isSelected =
                          activeEvidence &&
                          activeEvidence.document_id === ev.document_id &&
                          activeEvidence.page_number === ev.page_number &&
                          activeEvidence.quoted_span === ev.quoted_span;
                        return (
                          <button
                            type="button"
                            key={idx}
                            onClick={() => navigateToEvidence(ev)}
                            className={`inline-flex items-center gap-1 font-mono text-[10px] px-2 py-0.5 rounded-md border transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-400 ${
                              isSelected
                                ? 'bg-amber-100 text-amber-900 border-amber-400 font-bold ring-1 ring-amber-300 shadow-2xs'
                                : 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100 hover:border-indigo-300'
                            }`}
                            title={`Jump to ${ev.document_id} Page ${ev.page_number} to view citation`}
                          >
                            <FileCheck2 className={`w-3 h-3 ${isSelected ? 'text-amber-600' : 'text-indigo-500'}`} />
                            <span>{ev.document_id} (p.{ev.page_number})</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'facts' && (
          <div className="space-y-3 text-xs">
            {/* Applicant Identity Card */}
            <div className="p-3 rounded-lg border border-slate-200 bg-white space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-slate-800">
                <UserCheck className="w-4 h-4 text-indigo-600" />
                Applicant Identity
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 text-slate-600">
                <div>
                  <span className="text-slate-400 block text-[11px]">Full Name:</span>
                  <span className="font-medium text-slate-800">{state.applicant?.full_name || 'UNKNOWN'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">PAN (Masked):</span>
                  <span className="font-mono font-medium text-slate-800">{state.applicant?.pan_number || 'UNKNOWN'}</span>
                </div>
              </div>
            </div>

            {/* Payslip Card */}
            <div className="p-3 rounded-lg border border-slate-200 bg-white space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-slate-800">
                <TrendingUp className="w-4 h-4 text-emerald-600" />
                Payslip Reconciliation
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 text-slate-600">
                <div>
                  <span className="text-slate-400 block text-[11px]">Gross Salary:</span>
                  <span className="font-semibold text-slate-800">
                    {state.payslip?.gross_salary ? `₹${state.payslip.gross_salary.amount.toLocaleString('en-IN')}` : 'UNKNOWN'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Net Salary:</span>
                  <span className="font-semibold text-emerald-700">
                    {state.payslip?.net_salary ? `₹${state.payslip.net_salary.amount.toLocaleString('en-IN')}` : 'UNKNOWN'}
                  </span>
                </div>
                <div className="col-span-2">
                  <span className="text-slate-400 block text-[11px]">Employer:</span>
                  <span className="font-medium text-slate-700">{state.payslip?.employer_name || 'UNKNOWN'}</span>
                </div>
              </div>
            </div>

            {/* Bank Statement Card */}
            <div className="p-3 rounded-lg border border-slate-200 bg-white space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-slate-800">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
                Bank Statement Audit
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 text-slate-600">
                <div>
                  <span className="text-slate-400 block text-[11px]">Bank:</span>
                  <span className="font-medium text-slate-800">{state.bank_statement?.bank_name || 'UNKNOWN'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Account (Masked):</span>
                  <span className="font-mono text-slate-800">{state.bank_statement?.account_number_masked || 'UNKNOWN'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Avg Salary Credit:</span>
                  <span className="font-semibold text-blue-700">
                    {state.bank_statement?.average_salary_credit ? `₹${state.bank_statement.average_salary_credit.amount.toLocaleString('en-IN')}` : 'UNKNOWN'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Bounced Transactions:</span>
                  <span className="font-bold text-slate-800">{state.bank_statement?.bounced_transactions ?? 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'cam' && (
          <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 space-y-2">
            <h4 className="text-xs font-bold text-slate-800">Credit Appraisal Memo Narrative</h4>
            <div className="text-xs text-slate-700 whitespace-pre-line leading-relaxed font-sans">
              {state.summary_markdown || 'No summary synthesized yet.'}
            </div>
          </div>
        )}
      </div>
      )}

      {/* Quick Policy Q&A Drawer Bar (when viewing Findings, Facts, or CAM) */}
      {activeTab !== 'qa' && (
        <div className="px-3.5 py-2 bg-indigo-50/70 border-t border-indigo-100 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-1.5 text-xs text-indigo-900 font-medium">
            <HelpCircle className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
            <span>Need policy guidance or citation inquiry?</span>
          </div>
          <button
            type="button"
            onClick={() => setActiveTab('qa')}
            className="text-[11px] font-semibold px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-700 text-white transition-colors flex items-center gap-1 shadow-2xs cursor-pointer"
          >
            <span>Open Q&A</span>
            <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      )}

{pendingDecision && (
  <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
    <div className="w-full max-w-sm rounded-xl bg-white border border-slate-200 shadow-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <Info className="w-5 h-5 text-indigo-600" />
        <h3 className="text-sm font-bold text-slate-900">
          Confirm Review Decision
        </h3>
      </div>

      <p className="text-xs text-slate-600 leading-relaxed mb-4">
        Are you sure you want to{' '}
        <strong>
          {pendingDecision === 'APPROVED'
            ? 'approve'
            : pendingDecision === 'REJECTED'
            ? 'reject'
            : 'request more information for'}
        </strong>{' '}
        application <strong>{state.application_id}</strong>?
      </p>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setPendingDecision(null)}
          className="flex-1 py-2 px-3 rounded-lg border border-slate-300 bg-white text-slate-700 font-semibold text-xs hover:bg-slate-50"
        >
          Cancel
        </button>

        <button
          type="button"
          onClick={confirmDecision}
          className={`flex-1 py-2 px-3 rounded-lg text-white font-semibold text-xs ${
            pendingDecision === 'APPROVED'
              ? 'bg-emerald-600 hover:bg-emerald-700'
              : pendingDecision === 'REJECTED'
              ? 'bg-rose-600 hover:bg-rose-700'
              : 'bg-amber-500 hover:bg-amber-600'
          }`}
        >
          Confirm
        </button>
      </div>
    </div>
  </div>
)}

      {/* Human Review Sign-Off Footer */}
      <div className="p-4 border-t border-slate-200 bg-slate-50 shrink-0 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
            <Info className="w-4 h-4 text-indigo-600" />
            Human Review Sign-Off
          </div>
          <span className="text-[10px] uppercase tracking-wider font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
            Checkpoint Paused
          </span>
        </div>

        <textarea
          rows={2}
          value={reviewerNotes}
          onChange={(e) => setReviewerNotes(e.target.value)}
          placeholder="Enter underwriter sign-off notes or discrepancy rationale..."
          className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
        />

        {submittingDecision && (
          <div className="p-2 rounded bg-indigo-50 border border-indigo-200 text-xs text-indigo-800">
            Recorded Decision: <strong>{submittingDecision}</strong>
          </div>
        )}

        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => handleDecisionClick('APPROVED')}
            className="flex items-center justify-center gap-1 py-2 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition-colors shadow-xs"
          >
            <ThumbsUp className="w-3.5 h-3.5" />
            Approve
          </button>
          <button
            onClick={() => handleDecisionClick('REJECTED')}
            className="flex items-center justify-center gap-1 py-2 px-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs transition-colors shadow-xs"
          >
            <ThumbsDown className="w-3.5 h-3.5" />
            Reject
          </button>
          <button
            onClick={() => handleDecisionClick('NEEDS_INFO')}
            className="flex items-center justify-center gap-1 py-2 px-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold text-xs transition-colors shadow-xs"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            Need Info
          </button>
        </div>
      </div>
    </aside>
  );
};
