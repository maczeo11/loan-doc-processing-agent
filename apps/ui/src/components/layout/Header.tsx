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
}

export const Header: React.FC<HeaderProps> = ({
  selectedAppId,
  onSelectAppId,
  status,
  createdAt,
  onOpenShortcuts,
}) => {
  const { user, switchPersona } = useAuth();

  return (
    <header className="h-14 min-h-[56px] bg-white border-b border-terminal-border px-5 flex items-center justify-between select-none z-30 shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
      {/* Brand & Dossier Switcher */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-sm bg-[#0F172A] flex items-center justify-center text-[#F59E0B] shadow-sm">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif font-bold tracking-tight text-stone-900 text-base">FinScan AI</span>
              <span className="text-[10px] uppercase tracking-wider font-mono font-semibold px-1.5 py-0.5 bg-stone-100 text-stone-700 border border-stone-300 rounded-sm">
                CREDIT COMMITTEE
              </span>
            </div>
            <p className="text-[10px] font-sans text-stone-500 uppercase tracking-widest font-medium">
              Institutional Appraisal Desk
            </p>
          </div>
        </div>

        <div className="h-6 w-px bg-stone-200" />

        {/* Application Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-stone-500 font-medium">Dossier:</span>
          <select
            value={selectedAppId}
            onChange={(e) => onSelectAppId(e.target.value)}
            className="bg-[#F8F6F1] border border-[#D5CFC5] rounded-sm px-3 py-1.5 text-xs font-mono font-semibold text-stone-800 focus:outline-none focus:border-stone-800 transition-colors cursor-pointer shadow-inner"
          >
            <option value="APP-25195">APP-25195 (Clean Baseline • Aditya Sharma)</option>
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

      {/* Right: Auth Persona & Shortcuts Help */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenShortcuts}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm bg-[#F8F6F1] hover:bg-stone-200 text-stone-600 hover:text-stone-900 border border-stone-300 text-xs transition-colors"
          title="Keyboard Shortcuts Guide (?)"
        >
          <HelpCircle className="w-3.5 h-3.5 text-stone-700" />
          <kbd className="text-[10px] font-mono text-stone-500 font-bold">?</kbd>
        </button>

        <div className="h-6 w-px bg-stone-200" />

        {/* Persona Selector Dropdown */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-stone-100 border border-stone-300 overflow-hidden flex items-center justify-center text-stone-700 shadow-sm">
            {user?.avatarUrl ? (
              <img src={user.avatarUrl} alt={user.name} className="w-full h-full object-cover" />
            ) : (
              <UserCheck className="w-4 h-4 text-stone-800" />
            )}
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-stone-900 leading-tight">
              {user?.name || 'Reviewer'}
            </span>
            <select
              value={user?.role || 'SENIOR_UNDERWRITER'}
              onChange={(e) => switchPersona(e.target.value as UnderwriterRole)}
              className="bg-transparent text-[11px] text-stone-500 font-medium focus:outline-none cursor-pointer hover:text-stone-800 transition-colors"
            >
              <option value="SENIOR_UNDERWRITER" className="bg-white text-stone-900">
                Senior Underwriter
              </option>
              <option value="RISK_ANALYST" className="bg-white text-stone-900">
                Risk Analyst
              </option>
              <option value="COMPLIANCE_OFFICER" className="bg-white text-stone-900">
                Compliance Officer
              </option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
