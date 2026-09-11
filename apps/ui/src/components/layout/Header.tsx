import React from 'react';
import { ShieldCheck, UserCheck, HelpCircle } from 'lucide-react';
import { ApplicationStatus } from '../../types/application';
import { StatusPill } from '../common/StatusPill';
import { SlaTimer } from '../common/SlaTimer';
import { useAuth } from '../../context/AuthContext';
import { UnderwriterRole } from '../../types/auth';

interface HeaderProps {
  selectedAppId: string;
  onSelectAppId: (id: string) => void;
  status: ApplicationStatus;
  createdAt: string;
  onOpenShortcuts: () => void;
  liveApplications?: Array<{ application_id: string; applicant_name: string; status: string }>;
  onRefresh?: () => void;
  onOpenNewApplication?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  selectedAppId,
  onSelectAppId,
  status,
  createdAt,
  onOpenShortcuts,
  liveApplications = [],
  onRefresh,
  onOpenNewApplication,
}) => {
  const { user, switchPersona, logout } = useAuth();

  return (
    <header className="h-14 min-h-[56px] bg-theme-header border-b border-theme-border px-3 sm:px-5 flex items-center justify-between gap-3 select-none z-30 shadow-xs transition-colors duration-200">
      {/* Brand & Dossier Switcher */}
      <div className="flex items-center gap-3 sm:gap-5 min-w-0 shrink-0">
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

      {/* Center: Live Status & SLA Timer (collapses below xl) */}
      <div className="hidden xl:flex items-center gap-4 shrink-0">
        <StatusPill status={status} />
        <SlaTimer createdAt={createdAt} />
      </div>

      {/* Right: Shortcuts + User (ledger theme locked; no theme switcher) */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0 ml-auto">

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
            ) : (
              <UserCheck className="w-4 h-4 text-theme-primary" />
            )}
          </div>
          <div className="hidden lg:flex flex-col min-w-0">
            <span className="text-xs font-semibold text-theme-primary leading-tight truncate max-w-[140px]">
              {user?.name || 'Reviewer'}
            </span>
            <select
              value={user?.role || 'SENIOR_UNDERWRITER'}
              onChange={(e) => switchPersona(e.target.value as UnderwriterRole)}
              className="bg-transparent text-[11px] text-theme-muted font-medium focus:outline-none cursor-pointer hover:text-theme-primary transition-colors"
              title="Persona (mock mode; Google login locks role server-side)"
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
          </div>
          {logout ? (
            <button
              type="button"
              onClick={() => logout()}
              className="hidden sm:block text-[11px] font-mono text-theme-muted hover:text-theme-primary px-1.5 py-1"
              title="Sign out"
            >
              Logout
            </button>
          ) : null}
        </div>
      </div>
    </header>
  );
};
