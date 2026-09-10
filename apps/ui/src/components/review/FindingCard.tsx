import React from 'react';
import { Finding, EvidenceRef } from '../../types/evidence';
import { VerdictPill } from '../common/StatusPill';
import { getEvidenceKey } from '../../utils/coordinates';
import { sanitizePiiInText } from '../../utils/pii';
import { ExternalLink, Shield } from 'lucide-react';

interface FindingCardProps {
  finding: Finding;
  isFocused: boolean;
  onSelectFinding: () => void;
  onSelectEvidence: (ev: EvidenceRef, ruleId?: string) => void;
  activeEvidenceKey: string | null;
}

export const FindingCard: React.FC<FindingCardProps> = ({
  finding,
  isFocused,
  onSelectFinding,
  onSelectEvidence,
  activeEvidenceKey,
}) => {
  return (
    <div
      onClick={onSelectFinding}
      className={`p-3.5 rounded-xs border transition-all cursor-pointer ${
        isFocused
          ? 'bg-theme-card border-theme-brand shadow-sm ring-1 ring-theme-brand/30'
          : 'bg-theme-card hover:bg-theme-panel border-theme-border hover:border-theme-border-card'
      }`}
    >
      {/* Header: Rule ID & Verdict */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-theme-brand" />
          <span className="font-mono text-xs font-semibold text-theme-primary">
            {finding.rule_id}
          </span>
        </div>
        <VerdictPill verdict={finding.verdict} />
      </div>

      {/* Rule Name */}
      <h4 className="text-xs font-serif font-bold text-theme-primary tracking-tight mb-1.5">
        {finding.rule_name}
      </h4>

      {/* Verification Explanation */}
      <p className="text-xs text-theme-secondary leading-relaxed mb-3">
        {sanitizePiiInText(finding.reason)}
      </p>

      {/* Supporting Evidence Citations */}
      {finding.supporting_evidence.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-theme-border">
          <div className="text-[10px] uppercase tracking-wider font-semibold text-theme-muted flex items-center justify-between">
            <span>Verified Provenance ({finding.supporting_evidence.length})</span>
            <span className="text-[9px] text-theme-muted font-mono">Click to Jump</span>
          </div>

          <div className="flex flex-col gap-1.5">
            {finding.supporting_evidence.map((ev, idx) => {
              const key = getEvidenceKey(ev);
              const isActive = activeEvidenceKey === key;
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectEvidence(ev, finding.rule_id);
                  }}
                  className={`text-left p-2 rounded-xs border text-[11px] transition-all flex items-start justify-between gap-2 ${
                    isActive
                      ? 'bg-amber-500/15 border-amber-500/50 text-theme-primary shadow-xs ring-1 ring-amber-500/30'
                      : 'bg-theme-panel hover:bg-theme-card border-theme-border hover:border-theme-border-card text-theme-secondary'
                  }`}
                  title="Click to jump and highlight on PDF canvas"
                >
                  <div className="min-w-0 flex-1">
                    <span className="font-mono font-semibold text-amber-600 dark:text-amber-400 mr-1.5">
                      [{ev.document_type} • P.{ev.page_number}]
                    </span>
                    <span className="font-mono truncate block text-theme-primary mt-0.5 font-medium">
                      &ldquo;{sanitizePiiInText(ev.quoted_span)}&rdquo;
                    </span>
                  </div>
                  <ExternalLink className="w-3 h-3 text-theme-muted hover:text-theme-primary flex-shrink-0 mt-0.5" />
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Policy Footer */}
      <div className="mt-2.5 pt-2 border-t border-theme-border flex items-center justify-between text-[10px] text-theme-muted font-mono">
        <span>Policy v{finding.policy_version}</span>
        <span className="text-theme-secondary font-medium">Deterministic Rule</span>
      </div>
    </div>
  );
};
