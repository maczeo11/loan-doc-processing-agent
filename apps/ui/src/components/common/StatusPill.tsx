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
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono font-semibold bg-[#FEF3C7] border border-[#F59E0B] text-[#78350F] shadow-sm ${className}`}
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D97706] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#B45309]"></span>
          </span>
          <span className="tracking-wide uppercase">READY FOR REVIEW</span>
        </span>
      );

    case 'PROCESSING':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono font-semibold bg-[#F0F9FF] border border-[#BAE6FD] text-[#0369A1] ${className}`}
        >
          <Loader2 className="w-3.5 h-3.5 animate-spin text-[#0284C7]" />
          <span className="tracking-wide uppercase">PROCESSING</span>
        </span>
      );

    case 'REVIEWED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono font-semibold bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] shadow-sm ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-[#059669]" />
          <span className="tracking-wide uppercase">REVIEWED & SIGNED OFF</span>
        </span>
      );

    case 'NEEDS_INFORMATION':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono font-semibold bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E] ${className}`}
        >
          <HelpCircle className="w-3.5 h-3.5 text-[#D97706]" />
          <span className="tracking-wide uppercase">NEEDS INFORMATION</span>
        </span>
      );

    case 'FAILED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono font-semibold bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B] ${className}`}
        >
          <XCircle className="w-3.5 h-3.5 text-[#DC2626]" />
          <span className="tracking-wide uppercase">FAILED</span>
        </span>
      );

    case 'QUEUED':
    case 'UPLOADED':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-sm text-xs font-mono font-semibold bg-[#F5F5F4] border border-[#D6D3D1] text-[#44403C] ${className}`}
        >
          <Clock className="w-3.5 h-3.5 text-stone-500" />
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
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-mono font-bold tracking-wider uppercase bg-[#ECFDF5] border border-[#86EFAC] text-[#14532D] shadow-xs ${className}`}
      >
        <CheckCircle2 className="w-3 h-3 text-[#16A34A]" />
        <span>PASS</span>
      </span>
    );
  }
  if (verdict === 'flag') {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-mono font-bold tracking-wider uppercase bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] shadow-xs ${className}`}
      >
        <AlertCircle className="w-3 h-3 text-[#DC2626]" />
        <span>FLAG</span>
      </span>
    );
  }
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-mono font-bold tracking-wider uppercase bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E] shadow-xs ${className}`}
    >
      <HelpCircle className="w-3 h-3 text-[#D97706]" />
      <span>UNKNOWN</span>
    </span>
  );
};
