import React, { useState } from 'react';
import { Finding, EvidenceRef } from '../../types/evidence';
import { computeBoundingBoxPercent, getEvidenceKey } from '../../utils/coordinates';
import { sanitizePiiInText } from '../../utils/pii';
import { VerdictPill } from '../common/StatusPill';

interface EvidenceOverlayProps {
  documentId: string;
  pageNumber: number;
  findings: Finding[];
  activeEvidenceKey: string | null;
  onSelectEvidence: (evidence: EvidenceRef) => void;
}

export const EvidenceOverlay: React.FC<EvidenceOverlayProps> = ({
  documentId,
  pageNumber,
  findings,
  activeEvidenceKey,
  onSelectEvidence,
}) => {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  // Extract all citations relevant to this page of this document
  const pageEvidenceItems: Array<{
    evidence: EvidenceRef;
    finding: Finding;
    key: string;
  }> = [];

  findings.forEach((finding) => {
    finding.supporting_evidence.forEach((ev) => {
      if (ev.document_id === documentId && ev.page_number === pageNumber) {
        pageEvidenceItems.push({
          evidence: ev,
          finding,
          key: getEvidenceKey(ev),
        });
      }
    });
  });

  if (pageEvidenceItems.length === 0) {
    return null;
  }

  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {pageEvidenceItems.map(({ evidence, finding, key }) => {
        const percent = computeBoundingBoxPercent(evidence.bounding_box);
        const isActive = activeEvidenceKey === key;
        const isHovered = hoveredKey === key;

        let verdictClass = 'evidence-box-pass';
        if (finding.verdict === 'flag') verdictClass = 'evidence-box-flag';
        if (finding.verdict === 'unknown') verdictClass = 'evidence-box-unknown';

        return (
          <div
            key={key}
            onClick={(e) => {
              e.stopPropagation();
              onSelectEvidence(evidence);
            }}
            onMouseEnter={() => setHoveredKey(key)}
            onMouseLeave={() => setHoveredKey(null)}
            style={{
              left: `${percent.left}%`,
              top: `${percent.top}%`,
              width: `${percent.width}%`,
              height: `${percent.height}%`,
            }}
            className={`evidence-overlay-box ${verdictClass} ${
              isActive ? 'evidence-box-active' : ''
            }`}
          >
            {/* Tooltip on Hover or Active Focus */}
            {(isHovered || isActive) && (
              <div className="absolute left-0 bottom-full mb-1.5 z-40 min-w-[240px] max-w-sm rounded bg-slate-900/95 backdrop-blur-md border border-slate-700 shadow-xl p-2.5 text-slate-100 text-left pointer-events-none transition-all">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[10px] font-mono font-semibold text-indigo-400 uppercase">
                    {finding.rule_id}
                  </span>
                  <VerdictPill verdict={finding.verdict} />
                </div>
                <p className="text-[11px] text-slate-300 line-clamp-2 leading-relaxed mb-1.5">
                  &ldquo;{sanitizePiiInText(evidence.quoted_span)}&rdquo;
                </p>
                <div className="text-[9px] text-slate-400 flex items-center justify-between border-t border-slate-800 pt-1 font-mono">
                  <span>Page {evidence.page_number}</span>
                  <span>Verified Citation</span>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
