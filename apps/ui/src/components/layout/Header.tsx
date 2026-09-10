import React from 'react';
import { ShieldCheck, UserCheck, HelpCircle, Sparkles, Moon, BookOpen } from 'lucide-react';
import { ApplicationStatus } from '../../types/application';
import { StatusPill } from '../common/StatusPill';
import { SlaTimer } from '../common/SlaTimer';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { UnderwriterRole } from '../../types/auth';

interface HeaderProps {
  selectedAppId: string;
  onSelectAppId: (id: string) => void;
  status: ApplicationStatus;
  createdAt: string;
  onOpenShortcuts: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  selectedAppId,
  onSelectAppId,
  status,
  createdAt,
  onOpenShortcuts,
}) => {
  const { user, switchPersona } = useAuth();
  const { theme, setTheme } = useTheme();

  return (
    <header className="h-14 min-h-[56px] bg-theme-header border-b border-theme-border px-5 flex items-center justify-between select-none z-30 shadow-xs transition-colors duration-200">
      {/* Brand & Dossier Switcher */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-sm bg-[#0F172A] flex items-center justify-center text-[#F59E0B] shadow-sm ring-1 ring-white/10">
            <ShieldCheck className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif font-bold tracking-tight text-theme-primary text-base">
                FinScan AI
              </span>
              <span className="text-[10px] uppercase tracking-wider font-mono font-semibold px-1.5 py-0.5 bg-theme-panel text-theme-secondary border border-theme-border rounded-xs">
                CREDIT COMMITTEE
              </span>
            </div>
            <p className="text-[10px] font-sans text-theme-muted uppercase tracking-widest font-medium">
              Institutional Appraisal Desk
            </p>
          </div>
        </div>

        <div className="h-6 w-px bg-theme-border" />

        {/* Application Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-theme-muted font-medium">Dossier:</span>
          <select
            value={selectedAppId}
            onChange={(e) => onSelectAppId(e.target.value)}
            className="bg-theme-card border border-theme-border rounded-xs px-3 py-1.5 text-xs font-mono font-semibold text-theme-primary focus:outline-none focus:border-theme-brand transition-colors cursor-pointer shadow-2xs"
          >
            <option value="APP-25195">APP-25195 (Clean Baseline • Ananya Sharma)</option>
            <option value="APP-68210">APP-68210 (Salary Mismatch • Rajesh Verma)</option>
            <option value="APP-10492">APP-10492 (Identity Discrepancy • Pooja Iyer)</option>
          </select>
        </div>
      </div>

      {/* Center: Live Status & SLA Timer */}
      <div className="flex items-center gap-4">
        <StatusPill status={status} />
        <SlaTimer createdAt={createdAt} />
      </div>

      {/* Right: Theme Engine Selector, Auth Persona & Shortcuts */}
      <div className="flex items-center gap-3">
        {/* Live Theme Switcher Pill */}
        <div className="flex items-center bg-theme-panel border border-theme-border rounded-xs p-0.5 text-xs font-mono">
          <button
            type="button"
            onClick={() => setTheme('slate')}
            className={`flex items-center gap-1 px-2 py-1 rounded-xs transition-all ${
              theme === 'slate'
                ? 'bg-theme-card text-theme-primary font-bold shadow-xs border border-theme-border'
                : 'text-theme-muted hover:text-theme-primary'
            }`}
            title="Modern FinTech Slate Theme (Ramp / Linear / Stripe Terminal)"
          >
            <Sparkles className="w-3 h-3 text-indigo-500" />
            <span className="text-[11px]">Slate</span>
          </button>

          <button
            type="button"
            onClick={() => setTheme('ledger')}
            className={`flex items-center gap-1 px-2 py-1 rounded-xs transition-all ${
              theme === 'ledger'
                ? 'bg-theme-card text-theme-primary font-bold shadow-xs border border-theme-border'
                : 'text-theme-muted hover:text-theme-primary'
            }`}
            title="Swiss Archival Ledger Theme (Heritage Banking & FT Editorial)"
          >
            <BookOpen className="w-3 h-3 text-emerald-700" />
            <span className="text-[11px]">Ledger</span>
          </button>

          <button
            type="button"
            onClick={() => setTheme('obsidian')}
            className={`flex items-center gap-1 px-2 py-1 rounded-xs transition-all ${
              theme === 'obsidian'
                ? 'bg-theme-card text-theme-primary font-bold shadow-xs border border-theme-border'
                : 'text-theme-muted hover:text-theme-primary'
            }`}
            title="Obsidian Command Cockpit (Palantir Foundry / Bloomberg Dark)"
          >
            <Moon className="w-3 h-3 text-sky-400" />
            <span className="text-[11px]">Obsidian</span>
          </button>
        </div>

        <div className="h-6 w-px bg-theme-border" />

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

        {/* Persona Selector Dropdown */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-theme-panel border border-theme-border overflow-hidden flex items-center justify-center text-theme-secondary shadow-2xs">
            {user?.avatarUrl ? (
              <img src={user.avatarUrl} alt={user.name} className="w-full h-full object-cover" />
            ) : (
              <UserCheck className="w-4 h-4 text-theme-primary" />
            )}
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-theme-primary leading-tight">
              {user?.name || 'Reviewer'}
            </span>
            <select
              value={user?.role || 'SENIOR_UNDERWRITER'}
              onChange={(e) => switchPersona(e.target.value as UnderwriterRole)}
              className="bg-transparent text-[11px] text-theme-muted font-medium focus:outline-none cursor-pointer hover:text-theme-primary transition-colors"
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
        </div>
      </div>
    </header>
  );
};
