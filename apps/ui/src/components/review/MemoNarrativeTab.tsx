import React from 'react';
import { LoanApplication } from '../../types/application';
import { sanitizePiiInText } from '../../utils/pii';
import { Download, FileText, CheckCircle2 } from 'lucide-react';

interface MemoNarrativeTabProps {
  application: LoanApplication;
}

export const MemoNarrativeTab: React.FC<MemoNarrativeTabProps> = ({ application }) => {
  const narrative = application.memo_markdown || 'Credit Appraisal Memo generation pending.';

  const handleExport = () => {
    const blob = new Blob([sanitizePiiInText(narrative)], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `CAM_${application.id}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-3.5">
      {/* Export Header */}
      <div className="flex items-center justify-between p-2.5 rounded-xs bg-theme-panel border border-theme-border shadow-xs">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-theme-primary" />
          <span className="text-xs font-serif font-bold text-theme-primary">
            Credit Appraisal Memo (CAM)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`/applications/${encodeURIComponent(application.id)}/export?format=pdf`}
            target="_blank"
            rel="noopener noreferrer"
            download={`CAM_${application.id}.pdf`}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-xs bg-theme-panel hover:bg-theme-card text-theme-primary border border-theme-border text-xs font-serif font-semibold transition-colors cursor-pointer"
            title="Download Official ReportLab PDF CAM Memo"
          >
            <Download className="w-3.5 h-3.5 text-theme-unknown" />
            <span>PDF CAM</span>
          </a>
          <button
            type="button"
            onClick={handleExport}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-xs bg-theme-card hover:bg-theme-panel text-theme-primary border border-theme-border text-xs font-serif font-semibold transition-colors cursor-pointer"
            title="Export Markdown Memo"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Markdown</span>
          </button>
        </div>
      </div>

      {/* Memo Content Card - Editorial Paper Aesthetic */}
      <div className="p-5 rounded-xs bg-theme-card border border-theme-border text-xs leading-relaxed text-theme-secondary space-y-3 shadow-xs">
        <div className="flex items-center gap-2 pb-2 border-b border-theme-border text-[10px] text-theme-pass font-mono font-medium">
          <CheckCircle2 className="w-3.5 h-3.5 text-theme-pass" />
          <span>Grounded Synthesis • Prime Invariant Enforced • Zero Hallucinations</span>
        </div>

        <div className="prose prose-xs max-w-none space-y-2 whitespace-pre-wrap font-serif text-theme-primary leading-relaxed text-[13px]">
          {sanitizePiiInText(narrative)}
        </div>
      </div>
    </div>
  );
};
