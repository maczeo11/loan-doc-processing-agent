import React from 'react';
import { ApplicationStatus } from '../../types/application';
import { CheckCircle2, AlertCircle, HelpCircle, Loader2, XCircle, Clock } from 'lucide-react';

interface StatusPillProps {
  status: ApplicationStatus;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, className = '' }) => {
  switch (status) {
    case 'READY_FOR_REVIEW':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xs text-xs font-mono font-semibold bg-amber-500/15 border border-amber-500/40 text-amber-600 dark:text-amber-400 shadow-2xs ${className}`}
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-500 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-600"></span>
          </span>
          <span className="tracking-wide uppercase">READY FOR REVIEW</span>
        </span>
      );

    case 'PROCESSING':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xs text-xs font-mono font-semibold bg-sky-500/15 border border-sky-500/40 text-sky-600 dark:text-sky-400 ${className}`}
        >
          <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-500" />
          <span className="tracking-wide uppercase">PROCESSING</span>
        </span>
      );

    case 'REVIEWED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xs text-xs font-mono font-semibold bg-emerald-500/15 border border-emerald-500/40 text-emerald-700 dark:text-emerald-400 shadow-2xs ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
          <span className="tracking-wide uppercase">REVIEWED & SIGNED OFF</span>
        </span>
      );

    case 'NEEDS_INFORMATION':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xs text-xs font-mono font-semibold bg-amber-500/15 border border-amber-500/40 text-amber-700 dark:text-amber-400 ${className}`}
        >
          <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
          <span className="tracking-wide uppercase">NEEDS INFORMATION</span>
        </span>
      );

    case 'FAILED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xs text-xs font-mono font-semibold bg-rose-500/15 border border-rose-500/40 text-rose-700 dark:text-rose-400 ${className}`}
        >
          <XCircle className="w-3.5 h-3.5 text-rose-600" />
          <span className="tracking-wide uppercase">FAILED</span>
        </span>
      );

    case 'QUEUED':
    case 'UPLOADED':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xs text-xs font-mono font-semibold bg-theme-panel border border-theme-border text-theme-secondary ${className}`}
        >
          <Clock className="w-3.5 h-3.5 text-theme-muted" />
          <span className="tracking-wide uppercase">{status}</span>
        </span>
      );
  }
};

export const VerdictPill: React.FC<{
  verdict: 'pass' | 'flag' | 'unknown';
  className?: string;
}> = ({ verdict, className = '' }) => {
  if (verdict === 'pass') {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-xs text-[11px] font-mono font-bold tracking-wider uppercase bg-emerald-500/15 border border-emerald-500/40 text-emerald-700 dark:text-emerald-400 shadow-2xs ${className}`}
      >
        <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
        <span>PASS</span>
      </span>
    );
  }
  if (verdict === 'flag') {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-xs text-[11px] font-mono font-bold tracking-wider uppercase bg-rose-500/15 border border-rose-500/40 text-rose-700 dark:text-rose-400 shadow-2xs ${className}`}
      >
        <AlertCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
        <span>FLAG</span>
      </span>
    );
  }
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-xs text-[11px] font-mono font-bold tracking-wider uppercase bg-amber-500/15 border border-amber-500/40 text-amber-700 dark:text-amber-400 shadow-2xs ${className}`}
    >
      <HelpCircle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
      <span>UNKNOWN</span>
    </span>
  );
};
