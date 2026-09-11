import React, { useState } from 'react';
import { X, UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File, docTypeHint?: string) => Promise<void>;
  applicationId: string;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onUpload,
  applicationId,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [docTypeHint, setDocTypeHint] = useState<string>('auto');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<boolean>(false);
  const [uploadedCount, setUploadedCount] = useState<number>(0);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
      setErrorMessage(null);
    }
  };

  const autoDetectHint = (filename: string): string | undefined => {
    const f = filename.toLowerCase();
    if (f.includes('payslip') || f.includes('salary')) return 'payslip';
    if (f.includes('bank') || f.includes('statement')) return 'bank_statement';
    if (f.includes('tax') || f.includes('itr')) return 'tax_return';
    if (f.includes('pan') || f.includes('aadhaar') || f.includes('id')) return 'id_card';
    if (f.includes('app') || f.includes('form')) return 'application_form';
    return undefined;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFiles.length === 0) {
      setErrorMessage('Please select at least one PDF file to upload.');
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setUploadedCount(0);

    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const hint = docTypeHint === 'auto' ? autoDetectHint(file.name) : docTypeHint;
        await onUpload(file, hint);
        setUploadedCount(i + 1);
      }

      setUploadSuccess(true);
      setTimeout(() => {
        setUploadSuccess(false);
        setSelectedFiles([]);
        onClose();
      }, 1200);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 select-none">
      <div className="w-full max-w-md rounded-xs bg-theme-card border border-theme-border shadow-2xl overflow-hidden flex flex-col transition-colors duration-200 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-theme-border bg-theme-panel">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-xs bg-theme-brand/10 border border-theme-brand/20 flex items-center justify-center text-theme-brand">
              <UploadCloud className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-serif font-bold text-theme-primary">
                Upload Dossier Documents
              </h3>
              <p className="text-[10px] text-theme-muted font-mono uppercase tracking-wider">
                Container: {applicationId}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isUploading}
            className="p-1 rounded-xs text-theme-muted hover:text-theme-primary hover:bg-theme-panel-hover transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {errorMessage && (
            <div className="p-2.5 rounded-xs bg-theme-flag-bg border border-theme-flag-border text-theme-flag flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {uploadSuccess && (
            <div className="p-2.5 rounded-xs bg-theme-pass-bg border border-theme-pass-border text-theme-pass flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>
                {selectedFiles.length} {selectedFiles.length === 1 ? 'document' : 'documents'} uploaded successfully to {applicationId}.
              </span>
            </div>
          )}

          {/* File Picker */}
          <div>
            <label className="block font-mono font-bold text-theme-primary mb-1.5">
              Select Dossier PDF(s) *
            </label>
            <div className="border-2 border-dashed border-theme-border rounded-xs p-4 text-center hover:border-theme-brand transition-colors bg-theme-panel">
              <input
                type="file"
                accept=".pdf,application/pdf"
                multiple
                onChange={handleFileChange}
                className="hidden"
                id="dossier-batch-file-input"
              />
              <label
                htmlFor="dossier-batch-file-input"
                className="cursor-pointer flex flex-col items-center justify-center gap-1.5"
              >
                <FileText className="w-8 h-8 text-theme-muted" />
                <span className="text-xs font-mono font-semibold text-theme-brand hover:underline">
                  {selectedFiles.length > 0
                    ? `${selectedFiles.length} file(s) selected: ${selectedFiles.map((f) => f.name).join(', ')}`
                    : 'Choose one or more PDF files (multi-select supported)'}
                </span>
                <span className="text-[10px] text-theme-muted font-mono">
                  Standard institutional PDFs (Max 10 MB each)
                </span>
              </label>
            </div>
          </div>

          {/* Category Classification Hint */}
          <div className="space-y-1">
            <label className="font-mono font-bold text-theme-primary block">
              Document Category Hint
            </label>
            <select
              value={docTypeHint}
              onChange={(e) => setDocTypeHint(e.target.value)}
              className="w-full bg-theme-panel border border-theme-border rounded-xs px-3 py-2 text-xs font-sans text-theme-primary focus:outline-none focus:border-theme-brand shadow-2xs cursor-pointer"
            >
              <option value="auto">✨ Auto-Detect from Filename & Content</option>
              <option value="payslip">Salary Payslip</option>
              <option value="bank_statement">Bank Account Statement</option>
              <option value="tax_return">ITR Income Tax Return</option>
              <option value="id_card">KYC Identity Card (PAN / Aadhaar)</option>
              <option value="application_form">Loan Application Form</option>
            </select>
          </div>

          {/* Actions */}
          <div className="pt-2 flex items-center justify-end gap-2 border-t border-theme-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="px-3 py-2 rounded-xs border border-theme-border bg-theme-panel hover:bg-theme-panel-hover text-theme-secondary text-xs font-mono font-semibold transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={selectedFiles.length === 0 || isUploading || uploadSuccess}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xs text-xs font-mono font-bold bg-theme-brand hover:opacity-90 text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>
                    Uploading ({uploadedCount}/{selectedFiles.length})...
                  </span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>
                    Upload {selectedFiles.length > 0 ? `(${selectedFiles.length})` : 'Documents'}
                  </span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
