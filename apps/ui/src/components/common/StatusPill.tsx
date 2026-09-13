import React from 'react';
import { ApplicationStatus } from '../../types/application';
import { CheckCircle2, AlertCircle, HelpCircle, Loader2, XCircle, Clock, FileUp, Ban } from 'lucide-react';

/**
 * Ledger accent families. Every pill resolves to one of these four so the
 * chrome stays inside the three Swiss accents (racing green / claret /
 * tobacco) plus a neutral for in-flight states.
 */
const ACCENT = {
  pass: 'bg-theme-pass-bg border-theme-pass-border text-theme-pass',
  flag: 'bg-theme-flag-bg border-theme-flag-border text-theme-flag',
  unknown: 'bg-theme-unknown-bg border-theme-unknown-border text-theme-unknown',
  neutral: 'bg-theme-panel border-theme-border text-theme-secondary',
} as const;

type Accent = keyof typeof ACCENT;

const PILL_BASE =
  'inline-flex items-center gap-1.5 px-3 py-1 rounded-xs border text-xs font-mono font-semibold shadow-2xs';

interface StatusSpec {
  accent: Accent;
  label: string;
  icon: React.ReactNode;
}

/** Pulsing dot marking the one state that actually needs the underwriter. */
const PulseDot: React.FC = () => (
  <span className="relative flex h-2 w-2">
    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-theme-unknown opacity-75" />
    <span className="relative inline-flex h-2 w-2 rounded-full bg-theme-unknown" />
  </span>
);

const STATUS_SPECS: Partial<Record<ApplicationStatus | 'REVIEWED_REJECTED', StatusSpec>> = {
  READY_FOR_REVIEW: {
    accent: 'unknown',
    label: 'Ready for Review',
    icon: <PulseDot />,
  },
  UPLOADED: {
    accent: 'neutral',
    label: 'Uploaded',
    icon: <FileUp className="w-3.5 h-3.5 text-theme-muted" />,
  },
  QUEUED: {
    accent: 'neutral',
    label: 'Queued',
    icon: <Clock className="w-3.5 h-3.5 text-theme-muted" />,
  },
  PROCESSING: {
    accent: 'neutral',
    label: 'Processing',
    icon: <Loader2 className="w-3.5 h-3.5 animate-spin text-theme-muted" />,
  },
  CANCELLED: {
    accent: 'neutral',
    label: 'Cancelled',
    icon: <Ban className="w-3.5 h-3.5 text-theme-muted" />,
  },
  REVIEWED: {
    accent: 'pass',
    label: 'Reviewed & Signed Off',
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
  },
  REVIEWED_REJECTED: {
    accent: 'flag',
    label: 'Rejected & Closed',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  NEEDS_INFORMATION: {
    accent: 'unknown',
    label: 'Needs Information',
    icon: <HelpCircle className="w-3.5 h-3.5" />,
  },
  FAILED: {
    accent: 'flag',
    label: 'Failed',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
};

interface StatusPillProps {
  status: ApplicationStatus;
  /**
   * REVIEWED covers both approve and reject outcomes (see App.tsx
   * handleSubmitReview) — without this, a rejected dossier rendered the
   * identical green "Reviewed & Signed Off" pill as an approved one.
   */
  reviewerDecision?: string | null;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, reviewerDecision, className = '' }) => {
  const lookupKey = status === 'REVIEWED' && reviewerDecision === 'REJECTED' ? 'REVIEWED_REJECTED' : status;
  // Every ApplicationStatus has a spec; this covers unknown values from an
  // older or newer backend rather than printing a raw enum next to prose labels.
  const spec: StatusSpec = STATUS_SPECS[lookupKey] ?? {
    accent: 'neutral',
    label: status,
    icon: <Clock className="w-3.5 h-3.5 text-theme-muted" />,
  };

  return (
    <span className={`${PILL_BASE} ${ACCENT[spec.accent]} ${className}`}>
      {spec.icon}
      <span className="tracking-wide uppercase">{spec.label}</span>
    </span>
  );
};

type Verdict = 'pass' | 'flag' | 'unknown';

const VERDICT_SPECS: Record<Verdict, { label: string; icon: React.ReactNode }> = {
  pass: { label: 'PASS', icon: <CheckCircle2 className="w-3 h-3" /> },
  flag: { label: 'FLAG', icon: <AlertCircle className="w-3 h-3" /> },
  unknown: { label: 'UNKNOWN', icon: <HelpCircle className="w-3 h-3" /> },
};

export const VerdictPill: React.FC<{
  verdict: Verdict;
  className?: string;
}> = ({ verdict, className = '' }) => {
  const spec = VERDICT_SPECS[verdict];

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-xs border text-[11px] font-mono font-bold tracking-wider uppercase shadow-2xs ${ACCENT[verdict]} ${className}`}
    >
      {spec.icon}
      <span>{spec.label}</span>
    </span>
  );
};
