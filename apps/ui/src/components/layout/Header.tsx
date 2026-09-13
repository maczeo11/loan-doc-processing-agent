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
    <header className="h-14 min-h-[56px] bg-theme-header border-b border-theme-border px-3 sm:px-5 flex items-center justify-between gap-3 select-none z-30 shadow-xs transition-colors duration-200">
      {/* Brand & Dossier Switcher.
          `shrink-0` here meant this group never yielded width, so the right-hand
          cluster (shortcuts, user chip, logout) was pushed past the viewport
          edge and clipped at every breakpoint. It shrinks now; the dossier
          select truncates instead. */}
      <div className="flex items-center gap-3 sm:gap-5 min-w-0 shrink">
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-sm bg-theme-brand flex items-center justify-center text-white shadow-sm ring-1 ring-theme-border">
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
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-theme-muted font-medium hidden lg:inline shrink-0">Dossier:</span>
          <select
            value={selectedAppId}
            onChange={(e) => onSelectAppId(e.target.value)}
            className="bg-theme-card border border-theme-border rounded-xs px-3 py-1.5 text-xs font-mono font-semibold text-theme-primary focus:outline-none focus:border-theme-brand transition-colors cursor-pointer shadow-2xs max-w-[180px] sm:max-w-[280px] truncate"
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
              className="px-2 py-1 bg-theme-panel hover:bg-theme-card border border-theme-border rounded-xs text-[11px] font-mono text-theme-secondary hover:text-theme-primary transition-colors cursor-pointer"
              title="Refresh live applications from backend"
            >
              ↻ Refresh
            </button>
          )}
          {onOpenNewApplication && (
            <button
              type="button"
              onClick={onOpenNewApplication}
              className="flex items-center gap-1 px-2.5 py-1 bg-theme-brand hover:opacity-90 text-white rounded-xs text-[11px] font-mono font-bold transition-all shadow-xs cursor-pointer"
              title="Initialize a new loan application container"
            >
              <span>+ New</span>
            </button>
          )}
        </div>
      </div>

      {/* Center: Live Status & SLA Timer. The status pill is the single most
          important signal on the screen, so it stays visible from md up; only
          the wider SLA readout waits for xl. */}
      <div className="hidden md:flex items-center gap-4 shrink-0">
        <StatusPill status={status} />
        {/* The SLA readout is wide; at xl (1280) it crowded the header on the
            most common laptop width. It waits for 2xl now. */}
        <div className="hidden 2xl:block">
          <SlaTimer
            createdAt={createdAt}
            stopped={SEALED_STATUSES.includes(status)}
            stoppedAt={updatedAt}
          />
        </div>
      </div>

      {/* Right: Shortcuts + User (ledger theme locked; no theme switcher) */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0 ml-auto">

        {/* AI Quick Launch Button */}
        {onOpenCopilot && (
          <button
            type="button"
            onClick={onOpenCopilot}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs bg-theme-brand/10 hover:bg-theme-brand/20 text-theme-brand border border-theme-brand/30 hover:border-theme-brand text-xs font-mono font-bold transition-all shadow-2xs cursor-pointer group"
            title="Ask FinScan AI (Ctrl+K)"
          >
            <Sparkles className="w-3.5 h-3.5 text-theme-brand group-hover:rotate-12 transition-transform" />
            <span className="hidden sm:inline">Ask FinScan AI</span>
            <kbd className="hidden md:inline text-[9.5px] font-mono px-1 py-0.5 rounded-xs bg-theme-card border border-theme-border text-theme-muted">
              ^K
            </kbd>
          </button>
        )}

        {/* Shortcuts Button */}
        <button
          onClick={onOpenShortcuts}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs bg-theme-card hover:bg-theme-panel text-theme-secondary hover:text-theme-primary border border-theme-border text-xs transition-colors"
          title="Keyboard Shortcuts Guide (?)"
        >
          <HelpCircle className="w-3.5 h-3.5 text-theme-muted" />
          <kbd className="text-[10px] font-mono text-theme-muted font-bold">?</kbd>
        </button>

        <div className="h-6 w-px bg-theme-border" />

        {/* User chip (persona switch kept for mock mode; Google mode shows chip + logout) */}
        <div className="flex items-center gap-2.5">
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
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xs bg-theme-card hover:bg-theme-flag-bg text-theme-secondary hover:text-theme-flag border border-theme-border hover:border-theme-flag-border text-[11px] font-mono font-semibold transition-colors"
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
