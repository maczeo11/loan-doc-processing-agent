import React from 'react';
import {
  FileText,
  FileSpreadsheet,
  CreditCard,
  FileCheck,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { getDocumentTitle, getDocumentCategory } from '../../utils/documentHelper';

interface DocumentCardProps {
  documentId: string;
  documentType?: string;
  isSelected: boolean;
  onSelect: (documentId: string) => void;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({
  documentId,
  documentType,
  isSelected,
  onSelect,
}) => {
  const title = getDocumentTitle(documentId, documentType);
  const category = getDocumentCategory(documentType);

  const getDocIcon = (type?: string) => {
    switch (type) {
      case 'payslip':
        return <FileSpreadsheet className="w-4 h-4 text-emerald-600 shrink-0" />;
      case 'bank_statement':
        return <CreditCard className="w-4 h-4 text-blue-600 shrink-0" />;
      case 'tax_return':
        return <FileCheck className="w-4 h-4 text-indigo-600 shrink-0" />;
      case 'id_card':
        return <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0" />;
      default:
        return <FileText className="w-4 h-4 text-slate-500 shrink-0" />;
    }
  };

  return (
    <button
      type="button"
      onClick={() => onSelect(documentId)}
      className={`w-full text-left p-3 rounded-lg border transition-all text-xs flex flex-col gap-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 ${
        isSelected
          ? 'bg-indigo-50 border-indigo-300 shadow-sm ring-1 ring-indigo-200'
          : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50'
      }`}
    >
      <div className="flex items-center justify-between w-full gap-2">
        <div className="flex items-center gap-2 font-semibold text-slate-900 truncate">
          {getDocIcon(documentType)}
          <span className="truncate">{title}</span>
        </div>
        <CheckCircle2
          className={`w-3.5 h-3.5 shrink-0 ${
            isSelected ? 'text-indigo-600' : 'text-emerald-500'
          }`}
        />
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-0.5">
        <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 text-[10px]">
          {documentId}
        </span>
        <span className="font-medium text-slate-500">
          {category}
        </span>
      </div>
    </button>
  );
};
