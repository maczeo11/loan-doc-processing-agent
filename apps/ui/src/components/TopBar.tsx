import React from 'react';
import { ShieldCheck, RefreshCw, AlertCircle, Clock, CheckCircle2, User } from 'lucide-react';
import type { ApplicationStatus } from '../types/contracts';

interface TopBarProps {
  applicationId: string;
  applicantName?: string;
  status: ApplicationStatus;
  isDemoMode: boolean;
  isLoading: boolean;
  onRefresh: () => void;
  onToggleDemoMode: () => void;
  onExportJson: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  applicationId,
  applicantName = 'Applicant',
  status,
  isDemoMode,
  isLoading,
  onRefresh,
  onToggleDemoMode,
  onExportJson,
}) => {
  const getStatusBadge = (st: ApplicationStatus) => {
    switch (st) {
      case 'READY_FOR_REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300 shadow-sm">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            READY FOR REVIEW
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-300 animate-pulse">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            PROCESSING
          </span>
        );
      case 'REVIEWED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 border border-indigo-300">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
            REVIEWED (SIGNED OFF)
          </span>
        );
      case 'NEEDS_INFORMATION':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
            NEEDS INFORMATION
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
            FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            {st}
          </span>
        );
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 px-6 py-3.5 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Branding & Subtext */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 leading-none">
                FinScan AI
              </h1>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                Reviewer Workspace
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic code decides. AI explains. A human approves.
            </p>
          </div>
        </div>

        {/* Application Metadata & Actions */}
        <div className="flex items-center flex-wrap gap-3">
          <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
            <User className="w-4 h-4 text-slate-400" />
            <span className="font-medium text-slate-700">{applicantName}</span>
            <span className="text-slate-300">|</span>
            <span className="font-mono text-slate-600 font-semibold">{applicationId}</span>
          </div>

          <div>{getStatusBadge(status)}</div>

          {/* Mode Switcher */}
          <button
            onClick={onToggleDemoMode}
            className={`text-xs px-2.5 py-1.5 rounded-lg font-medium border transition-colors ${
              isDemoMode
                ? 'bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100'
                : 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
            }`}
            title={isDemoMode ? 'Using isolated demo dossier' : 'Connected to live FastAPI backend'}
          >
            {isDemoMode ? 'Demo Dossier (APP-25195)' : 'Live API Backend'}
          </button>

          {/* Export JSON Button */}
          <button
            onClick={onExportJson}
            className="text-xs px-2.5 py-1.5 rounded-lg font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors"
            title="Download reviewed dossier as JSON"
          >
            Export JSON
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors disabled:opacity-50"
            title="Refresh dossier status"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-indigo-600' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
