import React from 'react';
import { Lock } from 'lucide-react';
import { maskPan, maskAccountNumber, maskAadhaar } from '../../utils/pii';

interface MaskedValueProps {
  value?: string | null;
  type: 'pan' | 'account' | 'aadhaar';
  allowToggle?: boolean;
  className?: string;
}

export const MaskedValue: React.FC<MaskedValueProps> = ({
  value,
  type,
  className = '',
}) => {
  if (!value) {
    return <span className="text-theme-muted font-mono">—</span>;
  }

  let formatted = '';
  if (type === 'pan') formatted = maskPan(value);
  else if (type === 'account') formatted = maskAccountNumber(value);
  else if (type === 'aadhaar') formatted = maskAadhaar(value);

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono text-xs px-2 py-0.5 rounded-xs bg-theme-panel border border-theme-border text-theme-primary tabular-nums ${className}`}
      title="PII Masked per Security Invariant"
    >
      <Lock className="w-3 h-3 text-theme-muted flex-shrink-0" />
      <span className="tracking-wider">{formatted}</span>
    </span>
  );
};
