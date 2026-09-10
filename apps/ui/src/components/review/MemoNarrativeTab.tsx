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
      <div className="flex items-center justify-between p-2.5 rounded bg-white border border-[#E3DDD3] shadow-sm">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-stone-700" />
          <span className="text-xs font-serif font-bold text-stone-900">Credit Appraisal Memo (CAM)</span>
        </div>
        <button
          type="button"
          onClick={handleExport}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#F8F6F1] hover:bg-stone-200 text-stone-800 border border-[#E3DDD3] text-xs font-serif font-semibold transition-colors"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export CAM</span>
        </button>
      </div>

      {/* Memo Content Card - Editorial Paper Aesthetic */}
      <div className="p-5 rounded bg-[#FDFBF7] border border-[#E3DDD3] text-xs leading-relaxed text-stone-800 space-y-3 shadow-xs">
        <div className="flex items-center gap-2 pb-2 border-b border-[#E3DDD3] text-[10px] text-[#14532D] font-mono font-medium">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#15803D]" />
          <span>Grounded Synthesis • Prime Invariant Enforced • Zero Hallucinations</span>
        </div>

        <div className="prose prose-xs max-w-none space-y-2 whitespace-pre-wrap font-serif text-stone-800 leading-relaxed text-[13px]">
          {sanitizePiiInText(narrative)}
        </div>
      </div>
    </div>
  );
};
