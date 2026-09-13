import React from 'react';
import { ShieldCheck, UserCheck, HelpCircle, LogOut, Sparkles } from 'lucide-react';
import { ApplicationStatus } from '../../types/application';
import { StatusPill } from '../common/StatusPill';
import { SlaTimer } from '../common/SlaTimer';
import { useAuth } from '../../context/AuthContext';
import { initialsFor } from '../../services/auth';
import { UnderwriterRole } from '../../types/auth';

interface HeaderProps {
  selectedAppId: string;
  onSelectAppId: (id: string) => void;
  status: ApplicationStatus;
  reviewerDecision?: string | null;
  createdAt?: string;
  updatedAt?: string;
  onOpenShortcuts: () => void;
  onOpenCopilot?: () => void;
  liveApplications?: Array<{ application_id: string; applicant_name: string; status: string }>;
  onRefresh?: () => void;
  onOpenNewApplication?: () => void;
}

/** Terminal states stop the SLA clock rather than accruing a breach forever. */
const SEALED_STATUSES: ApplicationStatus[] = ['REVIEWED', 'CANCELLED', 'FAILED'];

export const Header: React.FC<HeaderProps> = ({
  selectedAppId,
  onSelectAppId,
  status,
  reviewerDecision,
  createdAt,
  updatedAt,
  onOpenShortcuts,
  onOpenCopilot,
  liveApplications = [],
  onRefresh,
  onOpenNewApplication,
}) => {
  const { user, mode, switchPersona, logout } = useAuth();
  // Google mode resolves the role server-side from the allowlist; letting the
  // reviewer pick a persona here implied an authority the server ignores.
  const personaLocked = mode === 'google';

  return (
    <header className="min-h-[56px] py-2 bg-theme-header border-b border-theme-border px-3 sm:px-5 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 select-none z-30 shadow-xs transition-colors duration-200">
      {/* Brand & Dossier Switcher (wraps and aligns cleanly on zoom) */}
      <div className="flex flex-wrap items-center gap-2.5 sm:gap-4 min-w-0">
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-sm bg-theme-brand flex items-center justify-center text-white shadow-sm ring-1 ring-theme-border shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div className="hidden sm:block">
            <div className="flex items-center gap-2">
              <span className="font-serif font-bold tracking-tight text-theme-primary text-base whitespace-nowrap">
                FinScan AI
              </span>
              <span className="text-[10px] uppercase tracking-wider font-mono font-semibold px-1.5 py-0.5 bg-theme-panel text-theme-secondary border border-theme-border rounded-xs whitespace-nowrap">
                CREDIT COMMITTEE
              </span>
            </div>
            <p className="text-[10px] font-sans text-theme-muted uppercase tracking-widest font-medium whitespace-nowrap">
              Institutional Appraisal Desk
            </p>
          </div>
        </div>

        <div className="h-6 w-px bg-theme-border hidden md:block" />

        {/* Application Selector */}
        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 flex-wrap">
          <span className="text-xs text-theme-muted font-medium hidden lg:inline shrink-0">Dossier:</span>
          <select
            value={selectedAppId}
            onChange={(e) => onSelectAppId(e.target.value)}
            className="bg-theme-card border border-theme-border rounded-xs px-2.5 py-1.5 text-xs font-mono font-semibold text-theme-primary focus:outline-none focus:border-theme-brand transition-colors cursor-pointer shadow-2xs max-w-[170px] sm:max-w-[260px] truncate"
          >
            {!selectedAppId && (
              <option value="">— Select or Create Dossier —</option>
            )}
            {liveApplications.length > 0 && (
              <optgroup label="🟢 Live Backend Applications">
                {liveApplications.map((app) => (
                  <option key={app.application_id} value={app.application_id}>
                    {app.application_id} • {app.applicant_name} ({app.status})
                  </option>
                ))}
              </optgroup>
            )}
            <optgroup label="📁 Offline Preset Archetypes">
              <option value="APP-25195">APP-25195 (Clean Baseline • Ananya Sharma)</option>
              <option value="APP-68210">APP-68210 (Salary Mismatch • Rajesh Verma)</option>
              <option value="APP-10492">APP-10492 (Identity Discrepancy • Pooja Iyer)</option>
            </optgroup>
          </select>
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="px-2 py-1 bg-theme-panel hover:bg-theme-card border border-theme-border rounded-xs text-[11px] font-mono text-theme-secondary hover:text-theme-primary transition-colors cursor-pointer shrink-0"
              title="Refresh live applications from backend"
            >
              ↻ Refresh
            </button>
          )}
          {onOpenNewApplication && (
            <button
              type="button"
              onClick={onOpenNewApplication}
              className="flex items-center gap-1 px-2.5 py-1 bg-theme-brand hover:opacity-90 text-white rounded-xs text-[11px] font-mono font-bold transition-all shadow-xs cursor-pointer shrink-0"
              title="Initialize a new loan application container"
            >
              <span>+ New</span>
            </button>
          )}
        </div>
      </div>

      {/* Center: Live Status & SLA Timer */}
      <div className="hidden xl:flex items-center gap-3 shrink-0">
        <StatusPill status={status} reviewerDecision={reviewerDecision} />
        <div className="hidden 2xl:block">
          <SlaTimer
            createdAt={createdAt}
            stopped={SEALED_STATUSES.includes(status)}
            stoppedAt={updatedAt}
          />
        </div>
      </div>

      {/* Right: Shortcuts + User (auto-aligns gracefully on high zoom) */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-2.5 shrink-0 ml-auto justify-end">

        {/* The Single Canonical FinScan AI Button */}
        {onOpenCopilot && (
          <button
            type="button"
            onClick={onOpenCopilot}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xs bg-theme-brand hover:opacity-90 text-white border border-theme-brand text-xs font-mono font-bold transition-all shadow-xs cursor-pointer group shrink-0"
            title="FinScan AI Copilot & Policy Q&A (Ctrl+K)"
          >
            <Sparkles className="w-3.5 h-3.5 text-white group-hover:rotate-12 transition-transform" />
            <span className="inline">FinScan AI</span>
            <kbd className="hidden sm:inline text-[9.5px] font-mono px-1.5 py-0.5 rounded-xs bg-white/20 text-white/95 border border-white/30">
              ^K
            </kbd>
          </button>
        )}

        {/* Shortcuts Button */}
        <button
          onClick={onOpenShortcuts}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs bg-theme-card hover:bg-theme-panel text-theme-secondary hover:text-theme-primary border border-theme-border text-xs transition-colors shrink-0"
          title="Keyboard Shortcuts Guide (?)"
        >
          <HelpCircle className="w-3.5 h-3.5 text-theme-muted" />
          <kbd className="text-[10px] font-mono text-theme-muted font-bold">?</kbd>
        </button>

        <div className="h-6 w-px bg-theme-border hidden sm:block" />

        {/* User chip */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-full bg-theme-panel border border-theme-border overflow-hidden flex items-center justify-center text-theme-secondary shadow-2xs shrink-0">
            {user?.avatarUrl ? (
              <img src={user.avatarUrl} alt={user.name} className="w-full h-full object-cover" />
            ) : user?.name ? (
              <span className="text-[11px] font-mono font-bold text-theme-primary">
                {initialsFor(user.name)}
              </span>
            ) : (
              <UserCheck className="w-4 h-4 text-theme-primary" />
            )}
          </div>
          <div className="hidden lg:flex flex-col min-w-0">
            <span className="text-xs font-semibold text-theme-primary leading-tight truncate max-w-[140px]">
              {user?.name || 'Reviewer'}
            </span>
            {personaLocked ? (
              <span
                className="text-[11px] text-theme-muted font-medium truncate max-w-[140px]"
                title="Role is assigned server-side from the Google allowlist"
              >
                {(user?.role || 'SENIOR_UNDERWRITER').replace(/_/g, ' ').toLowerCase()}
              </span>
            ) : (
              <select
                value={user?.role || 'SENIOR_UNDERWRITER'}
                onChange={(e) => switchPersona(e.target.value as UnderwriterRole)}
                className="bg-transparent text-[11px] text-theme-muted font-medium focus:outline-none cursor-pointer hover:text-theme-primary transition-colors"
                title="Persona switcher (mock mode only)"
              >
                <option value="SENIOR_UNDERWRITER" className="bg-theme-card text-theme-primary">
                  Senior Underwriter
                </option>
                <option value="RISK_ANALYST" className="bg-theme-card text-theme-primary">
                  Risk Analyst
                </option>
                <option value="COMPLIANCE_OFFICER" className="bg-theme-card text-theme-primary">
                  Compliance Officer
                </option>
              </select>
            )}
          </div>
          <button
            type="button"
            onClick={() => logout()}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs bg-theme-card hover:bg-theme-flag-bg text-theme-secondary hover:text-theme-flag border border-theme-border hover:border-theme-flag-border text-[11px] font-mono font-semibold transition-colors shrink-0"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};
