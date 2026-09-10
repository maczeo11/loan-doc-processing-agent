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
  onSelectEvidence: (ev: EvidenceRef) => void;
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
      className={`p-3.5 rounded border transition-all cursor-pointer ${
        isFocused
          ? 'bg-[#FDFBF7] border-stone-800 shadow-sm ring-1 ring-stone-700/20'
          : 'bg-white hover:bg-[#FDFBF7] border-[#E3DDD3] hover:border-stone-400'
      }`}
    >
      {/* Header: Rule ID & Verdict */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-stone-700" />
          <span className="font-mono text-xs font-semibold text-stone-800">
            {finding.rule_id}
          </span>
        </div>
        <VerdictPill verdict={finding.verdict} />
      </div>

      {/* Rule Name */}
      <h4 className="text-xs font-serif font-bold text-stone-900 tracking-tight mb-1.5">
        {finding.rule_name}
      </h4>

      {/* Verification Explanation */}
      <p className="text-xs text-stone-700 leading-relaxed mb-3">
        {sanitizePiiInText(finding.reason)}
      </p>

      {/* Supporting Evidence Citations */}
      {finding.supporting_evidence.length > 0 ? (
        <div className="space-y-1.5 pt-2 border-t border-[#E3DDD3]">
          <div className="text-[10px] uppercase tracking-wider font-semibold text-stone-500 flex items-center justify-between">
            <span>Verified Provenance ({finding.supporting_evidence.length})</span>
            <span className="text-[9px] text-stone-500 font-mono">Click to Jump</span>
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
                    onSelectEvidence(ev);
                  }}
                  className={`text-left p-2 rounded border text-[11px] transition-all flex items-start justify-between gap-2 ${
                    isActive
                      ? 'bg-[#FDF8EE] border-[#B45309] text-stone-900 shadow-sm'
                      : 'bg-[#FBF9F5] hover:bg-white border-[#E3DDD3] hover:border-stone-400 text-stone-800'
                  }`}
                  title="Click to jump and highlight on PDF canvas"
                >
                  <div className="min-w-0 flex-1">
                    <span className="font-mono font-semibold text-[#92400E] mr-1.5">
                      [{ev.document_type} • P.{ev.page_number}]
                    </span>
                    <span className="font-mono truncate block text-stone-800 mt-0.5 font-medium">
                      &ldquo;{sanitizePiiInText(ev.quoted_span)}&rdquo;
                    </span>
                  </div>
                  <ExternalLink className="w-3 h-3 text-stone-400 hover:text-stone-800 flex-shrink-0 mt-0.5" />
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="mt-2 p-2 rounded bg-[#FFFBEB] border border-[#D97706] text-[11px] font-mono text-[#92400E]">
          No supporting evidence attached — treat as UNVERIFIED and confirm manually.
        </div>
      )}

      {/* Policy Footer */}
      <div className="mt-2.5 pt-2 border-t border-[#E3DDD3] flex items-center justify-between text-[10px] text-stone-500 font-mono">
        <span>Policy v{finding.policy_version}</span>
        <span className="text-stone-600 font-medium">Deterministic Rule</span>
      </div>
    </div>
  );
};
