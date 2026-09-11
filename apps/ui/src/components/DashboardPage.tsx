import React, { useState } from 'react';
import { Plus, RefreshCw, FolderOpen, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export interface DashboardApp {
  application_id: string;
  applicant_name: string;
  status: string;
  loan_amount?: number;
  created_at?: string;
}

interface DashboardPageProps {
  apps: DashboardApp[];
  onRefresh: () => void;
  onOpen: (appId: string) => void;
  onNew: () => void;
  isLoading?: boolean;
}

const PRESETS: DashboardApp[] = [
  { application_id: 'APP-25195', applicant_name: 'Ananya Sharma (Clean Baseline)', status: 'READY_FOR_REVIEW' },
  { application_id: 'APP-68210', applicant_name: 'Rajesh Verma (Salary Mismatch)', status: 'READY_FOR_REVIEW' },
  { application_id: 'APP-10492', applicant_name: 'Pooja Iyer (Identity Discrepancy)', status: 'READY_FOR_REVIEW' },
];

/**
 * Real loan-app start: dashboard first (not empty viewer).
 * Lists live backend dossiers + offline presets, explicit New flow.
 */
export const DashboardPage: React.FC<DashboardPageProps> = ({ apps, onRefresh, onOpen, onNew, isLoading }) => {
  const { user } = useAuth();
  const [query, setQuery] = useState('');

  const q = query.trim().toLowerCase();
  const live = q ? apps.filter((a) => `${a.application_id} ${a.applicant_name} ${a.status}`.toLowerCase().includes(q)) : apps;
  const presets = q ? PRESETS.filter((a) => `${a.application_id} ${a.applicant_name}`.toLowerCase().includes(q)) : PRESETS;

  return (
    <div className="min-h-screen w-screen bg-theme-app text-theme-primary">
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
          {isLoading ? (
            <p className="p-5 text-xs text-theme-muted">Loading dossiers…</p>
          ) : live.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm font-serif font-bold mb-1">No live dossiers yet</p>
              <p className="text-xs text-theme-muted mb-3">When a customer walks in, create their dossier to begin upload → verify → review.</p>
              <button type="button" onClick={onNew} className="px-4 py-2 rounded-xs bg-theme-brand text-white text-xs font-bold">
                + Create first dossier
              </button>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-[11px] font-mono uppercase tracking-wider text-theme-muted border-b border-theme-border">
                  <th className="px-3 py-2">Application</th>
                  <th className="px-3 py-2">Applicant</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2 text-right">Open</th>
                </tr>
              </thead>
              <tbody>
                {live.map((a) => (
                  <tr key={a.application_id} className="border-b border-theme-border/60 last:border-0 hover:bg-theme-panel/60">
                    <td className="px-3 py-2.5 font-mono font-bold">{a.application_id}</td>
                    <td className="px-3 py-2.5">{a.applicant_name}</td>
                    <td className="px-3 py-2.5 font-mono">{a.status}</td>
                    <td className="px-3 py-2.5 text-right">
                      <button type="button" onClick={() => onOpen(a.application_id)} className="px-2.5 py-1 rounded-xs border border-theme-border hover:bg-theme-panel font-mono">
                        Open →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
