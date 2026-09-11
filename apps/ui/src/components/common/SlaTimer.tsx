import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';

interface SlaTimerProps {
  createdAt?: string | null;
  targetMinutes?: number;
  className?: string;
}

export const SlaTimer: React.FC<SlaTimerProps> = ({
  createdAt,
  targetMinutes = 15,
  className = '',
}) => {
  const [now, setNow] = useState<number>(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const parsedTime = createdAt ? new Date(createdAt).getTime() : NaN;
  const createdTime = isNaN(parsedTime) ? now : parsedTime;
  const elapsedMs = Math.max(0, now - createdTime);
  const totalBudgetMs = targetMinutes * 60 * 1000;
  const remainingMs = totalBudgetMs - elapsedMs;

  const elapsedSeconds = Math.floor(elapsedMs / 1000);
  const elapsedM = Math.floor(elapsedSeconds / 60);
  const elapsedS = elapsedSeconds % 60;

  const isBreached = remainingMs <= 0;
  const remainingSeconds = Math.abs(Math.floor(remainingMs / 1000));
  const remM = Math.floor(remainingSeconds / 60);
  const remS = remainingSeconds % 60;

  const pad = (n: number) => n.toString().padStart(2, '0');

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

  const createdDisplay = isNaN(parsedTime) ? 'Recent' : new Date(parsedTime).toLocaleTimeString();

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
