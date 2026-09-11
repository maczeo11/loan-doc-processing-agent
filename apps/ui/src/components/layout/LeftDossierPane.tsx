import React, { useState } from 'react';
import {
  FileText,
  CreditCard,
  Landmark,
  CheckCircle2,
  ShieldAlert,
  Upload,
  Layers,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { LoanApplication, DossierDocument } from '../../types/application';
import { MaskedValue } from '../common/MaskedValue';
import { formatCurrency } from '../../utils/pii';
import { DocumentUploadModal } from '../navigation/DocumentUploadModal';

interface LeftDossierPaneProps {
  application: LoanApplication;
  activeDocId: string;
  onSelectDocId: (id: string) => void;
  width: number;
  onUploadDocument?: (file: File, docTypeHint?: string) => Promise<void>;
}

export const LeftDossierPane: React.FC<LeftDossierPaneProps> = ({
  application,
  activeDocId,
  onSelectDocId,
  width,
  onUploadDocument,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const getDocIcon = (type: string) => {
    switch (type) {
      case 'PAYSLIP':
        return <CreditCard className="w-4 h-4 text-theme-pass" />;
      case 'BANK_STATEMENT':
        return <Landmark className="w-4 h-4 text-theme-brand" />;
      case 'TAX_RETURN':
        return <FileText className="w-4 h-4 text-theme-unknown" />;
      case 'ID_CARD':
        return <ShieldAlert className="w-4 h-4 text-theme-flag" />;
      default:
        return <FileText className="w-4 h-4 text-theme-muted" />;
    }
  };

  if (isCollapsed) {
    return (
      <aside className="w-12 h-full flex-none flex flex-col border-r border-theme-border bg-theme-panel select-none items-center py-3 justify-between transition-all duration-200">
        <div className="flex flex-col items-center gap-3">
          <button
            type="button"
            onClick={() => setIsCollapsed(false)}
            className="p-1.5 rounded-xs hover:bg-theme-panel-hover text-theme-secondary hover:text-theme-primary transition-colors"
            title="Expand Dossier Panel"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <div className="w-8 h-px bg-theme-border" />
          <div className="flex flex-col items-center gap-2">
            {application.documents.map((doc) => {
              const isSelected = activeDocId === doc.id;
              return (
                <button
                  key={doc.id}
                  onClick={() => onSelectDocId(doc.id)}
                  className={`p-2 rounded-xs transition-all relative ${
                    isSelected
                      ? 'bg-theme-card text-theme-brand border border-theme-border shadow-xs'
                      : 'text-theme-muted hover:text-theme-primary hover:bg-theme-panel-hover'
                  }`}
                  title={`${doc.name} (${doc.page_count} pages)`}
                >
                  {getDocIcon(doc.document_type)}
                  {isSelected && (
                    <div className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-theme-brand rounded-r" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside
      style={{ width: `${width}px` }}
      className="h-full flex-none flex flex-col border-r border-theme-border bg-theme-panel select-none overflow-hidden transition-colors duration-200"
    >
      {/* Top: Compact Applicant Metadata Card */}
      <div className="p-4 border-b border-theme-border bg-theme-card">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] uppercase tracking-widest font-bold text-theme-muted font-mono">
            Applicant Dossier
          </span>
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-mono font-bold text-theme-primary bg-theme-panel px-2 py-0.5 rounded-xs border border-theme-border">
              {application.id}
            </span>
            <button
              type="button"
              onClick={() => setIsCollapsed(true)}
              className="p-1 rounded-xs hover:bg-theme-panel text-theme-muted hover:text-theme-primary transition-colors"
              title="Collapse Panel"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <h2 className="text-sm font-serif font-bold text-theme-primary tracking-tight truncate">
          {application.applicant_name}
        </h2>
        <div className="mt-2.5 flex flex-col gap-1.5 text-xs">
          <div className="flex items-center justify-between text-theme-secondary">
            <span className="text-[11px] font-medium text-theme-muted">PAN / KYC:</span>
            <MaskedValue value={application.pan_masked} type="pan" />
          </div>
          <div className="flex items-center justify-between text-theme-secondary">
            <span className="text-[11px] font-medium text-theme-muted">Loan Amount:</span>
            <span className="font-mono font-bold text-theme-pass tabular-nums text-xs">
              {formatCurrency(application.loan_amount, application.currency)}
            </span>
          </div>
        </div>
      </div>

      {/* Middle: Dossier Document Tree Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-theme-border bg-theme-panel text-xs">
        <span className="text-[10px] font-mono font-bold text-theme-secondary uppercase tracking-wider flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-theme-muted" />
          <span>Dossier Index ({application.documents.length})</span>
        </span>
        <span className="text-[10px] text-theme-muted font-mono">[ / ]</span>
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {application.documents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-4 text-center border border-dashed border-theme-border rounded-xs bg-theme-panel/40">
            <div className="w-10 h-10 rounded-full bg-theme-panel border border-theme-border flex items-center justify-center text-theme-muted mb-2">
              <Upload className="w-5 h-5" />
            </div>
            <p className="text-xs font-serif font-bold text-theme-primary mb-1">
              No Documents in Dossier
            </p>
            <p className="text-[11px] text-theme-muted mb-3 leading-relaxed">
              Upload retail banking PDFs (Application, Payslips, Bank Statement, ITR, KYC) to initiate ingestion.
            </p>
            <button
              type="button"
              onClick={() => setIsUploadOpen(true)}
              className="px-3 py-1.5 rounded-xs bg-theme-brand hover:opacity-90 text-white text-xs font-mono font-bold transition-all shadow-xs cursor-pointer flex items-center gap-1.5"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload PDFs</span>
            </button>
          </div>
        ) : (
          application.documents.map((doc: DossierDocument) => {
            const isSelected = activeDocId === doc.id;
            return (
              <div
                key={doc.id}
                onClick={() => onSelectDocId(doc.id)}
                className={`p-3 rounded-xs border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-theme-card border-theme-brand shadow-xs ring-1 ring-theme-brand/30'
                    : 'bg-theme-card hover:bg-theme-panel border-theme-border hover:border-theme-border-card'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <div className="p-1.5 rounded-xs bg-theme-panel border border-theme-border flex-shrink-0 mt-0.5">
                    {getDocIcon(doc.document_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <p
                        className={`text-xs font-serif font-bold truncate ${
                          isSelected ? 'text-theme-primary' : 'text-theme-secondary'
                        }`}
                      >
                        {doc.name}
                      </p>
                      {doc.verified && (
                        <CheckCircle2 className="w-3.5 h-3.5 text-theme-pass flex-shrink-0" />
                      )}
                    </div>

                    <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-theme-muted font-mono">
                      <span className="px-1.5 py-0.5 rounded-xs bg-theme-panel border border-theme-border">
                        {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded-xs border font-semibold ${
                          doc.ocr_route === 'native'
                            ? 'bg-theme-pass-bg border-theme-pass-border text-theme-pass'
                            : 'bg-theme-unknown-bg border-theme-unknown-border text-theme-unknown'
                        }`}
                      >
                        {doc.ocr_route === 'native' ? 'Native Layer' : 'PaddleOCR'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Bottom: Supplemental Document Upload Button */}
      <div className="p-3 border-t border-theme-border bg-theme-card">
        <button
          type="button"
          onClick={() => setIsUploadOpen(true)}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xs border border-theme-border bg-theme-panel hover:bg-theme-panel-hover text-theme-primary text-xs font-mono font-semibold transition-colors shadow-2xs cursor-pointer"
        >
          <Upload className="w-3.5 h-3.5 text-theme-muted" />
          <span>Upload File</span>
        </button>
      </div>

      {/* Supplemental Document Upload Modal */}
      {onUploadDocument && (
        <DocumentUploadModal
          isOpen={isUploadOpen}
          onClose={() => setIsUploadOpen(false)}
          onUpload={onUploadDocument}
          applicationId={application.id}
        />
      )}
    </aside>
  );
};
