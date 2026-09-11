import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle2 } from 'lucide-react';

interface SlaTimerProps {
  createdAt?: string | null;
  targetMinutes?: number;
  /** True once the dossier is sealed — the clock stops instead of breaching. */
  stopped?: boolean;
  /** Timestamp the clock stopped at (the final transition). */
  stoppedAt?: string | null;
  className?: string;
}

export const SlaTimer: React.FC<SlaTimerProps> = ({
  createdAt,
  targetMinutes = 15,
  stopped = false,
  stoppedAt,
  className = '',
}) => {
  const [now, setNow] = useState<number>(Date.now());

  useEffect(() => {
    // A sealed dossier needs no ticking clock.
    if (stopped) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [stopped]);

  const parsedTime = createdAt ? new Date(createdAt).getTime() : NaN;
  const pad = (n: number) => n.toString().padStart(2, '0');

  // No known clock start means no SLA to report. Substituting `now` here made
  // the timer restart from full budget on every poll.
  if (Number.isNaN(parsedTime)) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-mono tabular-nums bg-theme-panel border-theme-border text-theme-muted ${className}`}
        title="No status transition recorded yet, so the SLA clock has not started"
      >
        <Clock className="w-3.5 h-3.5 flex-shrink-0" />
        <span>SLA NOT STARTED</span>
      </div>
    );
  }

  const endTime = stopped && stoppedAt ? new Date(stoppedAt).getTime() : now;
  const effectiveEnd = Number.isNaN(endTime) ? now : endTime;
  const elapsedMs = Math.max(0, effectiveEnd - parsedTime);
  const totalBudgetMs = targetMinutes * 60 * 1000;
  const remainingMs = totalBudgetMs - elapsedMs;

  const elapsedSeconds = Math.floor(elapsedMs / 1000);
  const elapsedM = Math.floor(elapsedSeconds / 60);
  const elapsedS = elapsedSeconds % 60;

  const isBreached = remainingMs <= 0;
  const remainingSeconds = Math.abs(Math.floor(remainingMs / 1000));
  const remM = Math.floor(remainingSeconds / 60);
  const remS = remainingSeconds % 60;

  const createdDisplay = new Date(parsedTime).toLocaleTimeString();

  // Sealed dossiers report the outcome, not a live countdown.
  if (stopped) {
    const withinSla = !isBreached;
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-mono tabular-nums ${
          withinSla
            ? 'text-theme-pass bg-theme-pass-bg border-theme-pass-border'
            : 'text-theme-flag bg-theme-flag-bg border-theme-flag-border'
        } ${className}`}
        title={`Target SLA: ${targetMinutes} mins | Created: ${createdDisplay}`}
      >
        <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
        <span>
          {withinSla ? 'CLOSED WITHIN SLA' : 'CLOSED OVER SLA'} ({pad(elapsedM)}:{pad(elapsedS)})
        </span>
      </div>
    );
  }

  // Color dynamics: green while comfortable, tobacco as the SLA nears,
  // claret once inside 3 minutes or breached.
  let colorClasses = 'text-theme-pass bg-theme-pass-bg border-theme-pass-border';
  if (isBreached) {
    colorClasses = 'text-theme-flag bg-theme-flag-bg border-theme-flag-border animate-pulse';
  } else if (remM < 3) {
    colorClasses = 'text-theme-flag bg-theme-flag-bg border-theme-flag-border';
  } else if (remM < 7) {
    colorClasses = 'text-theme-unknown bg-theme-unknown-bg border-theme-unknown-border';
  }

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-mono tabular-nums ${colorClasses} ${className}`}
      title={`Target SLA: ${targetMinutes} mins | Created: ${createdDisplay}`}
    >
      <Clock className="w-3.5 h-3.5 flex-shrink-0" />
      <span>
        {isBreached
          ? `SLA BREACHED +${pad(remM)}:${pad(remS)}`
          : `SLA ${pad(remM)}:${pad(remS)} REMAINING`}
      </span>
      <span className="opacity-60 text-[10px]">({pad(elapsedM)}:{pad(elapsedS)} ELAPSED)</span>
    </div>
  );
};
