import React from 'react';
import { FileText, CreditCard, Landmark, CheckCircle2, ShieldAlert, Upload, Layers } from 'lucide-react';
import { LoanApplication, DossierDocument } from '../../types/application';
import { MaskedValue } from '../common/MaskedValue';
import { formatCurrency } from '../../utils/pii';

interface LeftDossierPaneProps {
  application: LoanApplication;
  activeDocId: string;
  onSelectDocId: (id: string) => void;
  width: number;
}

export const LeftDossierPane: React.FC<LeftDossierPaneProps> = ({
  application,
  activeDocId,
  onSelectDocId,
  width,
}) => {
  const getDocIcon = (type: string) => {
    switch (type) {
      case 'PAYSLIP':
        return <CreditCard className="w-4 h-4 text-emerald-800" />;
      case 'BANK_STATEMENT':
        return <Landmark className="w-4 h-4 text-slate-800" />;
      case 'TAX_RETURN':
        return <FileText className="w-4 h-4 text-amber-800" />;
      case 'ID_CARD':
        return <ShieldAlert className="w-4 h-4 text-stone-800" />;
      default:
        return <FileText className="w-4 h-4 text-stone-600" />;
    }
  };

  return (
    <aside
      style={{ width: `${width}px` }}
      className="h-full flex-none flex flex-col border-r border-[#E3DDD3] bg-[#FBF9F5] select-none overflow-hidden"
    >
      {/* Top: Compact Applicant Metadata Card */}
      <div className="p-4 border-b border-[#E3DDD3] bg-white">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] uppercase tracking-widest font-bold text-stone-500 font-mono">
            Applicant Dossier
          </span>
          <span className="text-[11px] font-mono font-bold text-stone-800 bg-[#F2EDE4] px-2 py-0.5 rounded-sm border border-[#DCD5C9]">
            {application.id}
          </span>
        </div>
        <h2 className="text-sm font-serif font-bold text-stone-900 tracking-tight truncate">
          {application.applicant_name}
        </h2>
        <div className="mt-2.5 flex flex-col gap-1.5 text-xs">
          <div className="flex items-center justify-between text-stone-600">
            <span className="text-[11px] font-medium">PAN / KYC:</span>
            <MaskedValue value={application.pan_masked} type="pan" />
          </div>
          <div className="flex items-center justify-between text-stone-600">
            <span className="text-[11px] font-medium">Loan Amount:</span>
            <span className="font-mono font-bold text-[#14532D] tabular-nums text-xs">
              {formatCurrency(application.loan_amount, application.currency)}
            </span>
          </div>
        </div>
      </div>

      {/* Middle: Dossier Document Tree Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#E3DDD3] bg-[#F2EDE4]/60">
        <span className="text-[10px] font-mono font-bold text-stone-700 uppercase tracking-wider flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-stone-600" />
          <span>Dossier Index ({application.documents.length})</span>
        </span>
        <span className="text-[10px] text-stone-500 font-mono">[ / ]</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {application.documents.map((doc: DossierDocument) => {
          const isSelected = activeDocId === doc.id;
          return (
            <div
              key={doc.id}
              onClick={() => onSelectDocId(doc.id)}
              className={`p-3 rounded-sm border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-white border-[#0F172A] shadow-xs ring-1 ring-[#0F172A]'
                  : 'bg-white hover:bg-[#F8F6F1] border-[#E3DDD3] hover:border-stone-400'
              }`}
            >
              <div className="flex items-start gap-2.5">
                <div className="p-1.5 rounded-sm bg-[#F8F6F1] border border-[#E3DDD3] flex-shrink-0 mt-0.5">
                  {getDocIcon(doc.document_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <p className={`text-xs font-serif font-bold truncate ${isSelected ? 'text-stone-950' : 'text-stone-800'}`}>
                      {doc.name}
                    </p>
                    {doc.verified && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700 flex-shrink-0" />
                    )}
                  </div>

                  <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-stone-600 font-mono">
                    <span className="px-1.5 py-0.5 rounded-sm bg-[#F8F6F1] border border-[#E3DDD3]">
                      {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded-sm border font-semibold ${
                        doc.ocr_route === 'native'
                          ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                          : 'bg-amber-50 border-amber-300 text-amber-900'
                      }`}
                    >
                      {doc.ocr_route === 'native' ? 'Native Layer' : 'PaddleOCR'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom: Supplemental Document Upload Button */}
      <div className="p-3 border-t border-[#E3DDD3] bg-white">
        <button
          type="button"
          onClick={() => alert('Document upload handler: In production, invokes POST /applications/{id}/documents to append supplemental dossier files.')}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-sm border border-[#D5CFC5] bg-[#F8F6F1] hover:bg-[#EFEAE1] text-stone-800 text-xs font-mono font-semibold transition-colors shadow-2xs"
        >
          <Upload className="w-3.5 h-3.5 text-stone-700" />
          <span>Upload File</span>
        </button>
      </div>
    </aside>
  );
};
