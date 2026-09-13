import React, { useMemo, useState } from 'react';
import { Plus, RefreshCw, FolderOpen, ShieldCheck, AlertTriangle, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { StatusPill } from './common/StatusPill';
import { formatCurrency } from '../utils/pii';
import type { ApplicationStatus } from '../types/application';

export interface DashboardApp {
  application_id: string;
  applicant_name: string;
  status: string;
  loan_amount?: number;
  loan_purpose?: string | null;
  created_at?: string;
}

interface DashboardPageProps {
  apps: DashboardApp[];
  onRefresh: () => void;
  onOpen: (appId: string) => void;
  onNew: () => void;
  isLoading?: boolean;
  /** Set when the dossier list could not be fetched at all. */
  backendError?: string | null;
}

const PRESETS: DashboardApp[] = [
  { application_id: 'APP-25195', applicant_name: 'Ananya Sharma (Clean Baseline)', status: 'READY_FOR_REVIEW' },
  { application_id: 'APP-68210', applicant_name: 'Rajesh Verma (Salary Mismatch)', status: 'READY_FOR_REVIEW' },
  { application_id: 'APP-10492', applicant_name: 'Pooja Iyer (Identity Discrepancy)', status: 'READY_FOR_REVIEW' },
];

/** Dossiers needing a human first; then newest. */
const STATUS_PRIORITY: Record<string, number> = {
  READY_FOR_REVIEW: 0,
  NEEDS_INFORMATION: 1,
  PROCESSING: 2,
  QUEUED: 3,
  UPLOADED: 4,
  FAILED: 5,
  REVIEWED: 6,
  CANCELLED: 7,
};

function relativeAge(iso?: string): string {
  if (!iso) return '—';
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return '—';
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Real loan-app start: dashboard first (not empty viewer).
 * Lists live backend dossiers + offline presets, explicit New flow.
 */
export const DashboardPage: React.FC<DashboardPageProps> = ({
  apps,
  onRefresh,
  onOpen,
  onNew,
  isLoading,
  backendError,
}) => {
  const { user, logout } = useAuth();
  const [query, setQuery] = useState('');

  const q = query.trim().toLowerCase();
  const live = useMemo(() => {
    const filtered = q
      ? apps.filter((a) => `${a.application_id} ${a.applicant_name} ${a.status}`.toLowerCase().includes(q))
      : apps;
    // Queue order, not insertion order: what needs a decision comes first.
    return [...filtered].sort((a, b) => {
      const byStatus = (STATUS_PRIORITY[a.status] ?? 9) - (STATUS_PRIORITY[b.status] ?? 9);
      if (byStatus !== 0) return byStatus;
      return (b.created_at || '').localeCompare(a.created_at || '');
    });
  }, [apps, q]);
  const presets = q ? PRESETS.filter((a) => `${a.application_id} ${a.applicant_name}`.toLowerCase().includes(q)) : PRESETS;
  const awaitingReview = apps.filter((a) => a.status === 'READY_FOR_REVIEW').length;

  return (
    <div className="min-h-full w-full bg-theme-app text-theme-primary">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-sm bg-theme-brand flex items-center justify-center text-white">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-serif font-bold text-xl">Dossier Desk</h1>
              <p className="text-xs text-theme-muted font-mono">
                {user ? `Signed in as ${user.name} (${user.role})` : 'FinScan AI — retail loan underwriting'}
                {awaitingReview > 0 && (
                  <span className="text-theme-unknown font-bold">
                    {' '}· {awaitingReview} awaiting review
                  </span>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onRefresh}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xs bg-theme-card border border-theme-border text-xs hover:bg-theme-panel"
              title="Reload dossiers"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
            <button
              type="button"
              onClick={onNew}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xs bg-theme-brand text-white text-xs font-bold hover:opacity-90"
            >
              <Plus className="w-3.5 h-3.5" /> New Application
            </button>
            {/* This is the landing view after sign-in - before opening any
                dossier, Header.tsx (which has the only other logout button)
                never mounts. Without this, a freshly-logged-in user has no
                way to sign out at all until they open a specific dossier. */}
            {user && (
              <button
                type="button"
                onClick={() => logout()}
                className="flex items-center gap-1.5 px-2.5 py-2 rounded-xs bg-theme-card hover:bg-theme-flag-bg text-theme-secondary hover:text-theme-flag border border-theme-border hover:border-theme-flag-border text-xs font-mono font-semibold transition-colors"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            )}
          </div>
        </div>

        <div className="bg-theme-card border border-theme-border rounded-xs p-3 mb-5 flex items-center gap-2">
          <FolderOpen className="w-4 h-4 text-theme-muted shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by APP-ID, applicant, or status…"
            className="w-full bg-transparent text-sm focus:outline-none placeholder:text-theme-muted"
          />
        </div>

        <h2 className="text-xs font-mono uppercase tracking-widest text-theme-muted mb-2">
          Live backend dossiers ({live.length})
        </h2>
        <div className="bg-theme-card border border-theme-border rounded-xs overflow-hidden mb-6">
          {/* An unreachable backend is stated plainly. Rendering the "no
              dossiers yet" empty state for a connection failure invited the
              reviewer to create duplicates of work that already exists. */}
          {backendError ? (
            <div className="p-6 text-center">
              <div className="w-10 h-10 rounded-full bg-theme-flag-bg border border-theme-flag-border flex items-center justify-center text-theme-flag mx-auto mb-2">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <p className="text-sm font-serif font-bold mb-1">Cannot reach the FinScan API</p>
              <p className="text-xs text-theme-muted mb-3 font-mono break-words max-w-md mx-auto">
                {backendError}
              </p>
              <button
                type="button"
                onClick={onRefresh}
                className="px-4 py-2 rounded-xs border border-theme-border hover:bg-theme-panel text-xs font-mono font-bold"
              >
                Retry
              </button>
            </div>
          ) : isLoading && live.length === 0 ? (
            <p className="p-5 text-xs text-theme-muted">Loading dossiers…</p>
          ) : live.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm font-serif font-bold mb-1">
                {q ? 'No dossiers match that search' : 'No live dossiers yet'}
              </p>
              <p className="text-xs text-theme-muted mb-3">
                {q
                  ? 'Clear the search to see every dossier on the desk.'
                  : 'When a customer walks in, create their dossier to begin upload → verify → review.'}
              </p>
              {!q && (
                <button type="button" onClick={onNew} className="px-4 py-2 rounded-xs bg-theme-brand text-white text-xs font-bold">
                  + Create first dossier
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs min-w-[640px]">
                <thead>
                  <tr className="text-left text-[11px] font-mono uppercase tracking-wider text-theme-muted border-b border-theme-border">
                    <th className="px-3 py-2">Application</th>
                    <th className="px-3 py-2">Applicant</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Age</th>
                    <th className="px-3 py-2 text-right">Open</th>
                  </tr>
                </thead>
                <tbody>
                  {live.map((a) => (
                    <tr
                      key={a.application_id}
                      onClick={() => onOpen(a.application_id)}
                      className="border-b border-theme-border/60 last:border-0 hover:bg-theme-panel/60 cursor-pointer"
                    >
                      <td className="px-3 py-2.5 font-mono font-bold whitespace-nowrap">{a.application_id}</td>
                      <td className="px-3 py-2.5">
                        <span className="block truncate max-w-[200px]">{a.applicant_name}</span>
                        {a.loan_purpose && (
                          <span className="block text-[10px] text-theme-muted truncate max-w-[200px]">
                            {a.loan_purpose}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums whitespace-nowrap">
                        {typeof a.loan_amount === 'number' ? formatCurrency(a.loan_amount) : '—'}
                      </td>
                      <td className="px-3 py-2.5">
                        <StatusPill status={a.status as ApplicationStatus} />
                      </td>
                      <td className="px-3 py-2.5 font-mono text-theme-muted whitespace-nowrap">
                        {relativeAge(a.created_at)}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <span className="px-2.5 py-1 rounded-xs border border-theme-border font-mono inline-block">
                          Open →
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <h2 className="text-xs font-mono uppercase tracking-widest text-theme-muted mb-2">Offline preset archetypes</h2>
        <div className="grid sm:grid-cols-3 gap-3">
          {presets.map((p) => (
            <button
              key={p.application_id}
              type="button"
              onClick={() => onOpen(p.application_id)}
              className="text-left bg-theme-card border border-theme-border rounded-xs p-3.5 hover:bg-theme-panel transition-colors"
            >
              <span className="block font-mono font-bold text-xs mb-1">{p.application_id}</span>
              <span className="block text-xs text-theme-secondary mb-2">{p.applicant_name}</span>
              <span className="inline-block text-[11px] font-mono px-1.5 py-0.5 rounded-xs bg-theme-panel border border-theme-border text-theme-muted">
                {p.status}
              </span>
            </button>
          ))}
        </div>

        <p className="text-[11px] text-theme-muted mt-6 leading-relaxed">
          Flow: <b>New Application</b> → upload 5 doc types → <b>Run FinScan Verification Pipeline</b> → wait for{' '}
          <code>READY_FOR_REVIEW</code> → audit flags → policy Q&amp;A → sign-off (<code>A/R/N</code> + rationale + type{' '}
          <code>APP-XXXXX</code>). System never auto-approves.
        </p>
      </div>
    </div>
  );
};
