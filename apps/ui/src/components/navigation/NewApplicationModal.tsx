import React, { useState } from 'react';
import { X, UserPlus, IndianRupee, Briefcase, FileText, Loader2 } from 'lucide-react';

export interface NewApplicationPayload {
  applicant_name: string;
  loan_amount: number;
  loan_purpose: string;
}

interface NewApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate?: (payload: NewApplicationPayload) => Promise<void>;
  onSubmit?: (payload: NewApplicationPayload) => Promise<void>;
}

export const NewApplicationModal: React.FC<NewApplicationModalProps> = ({
  isOpen,
  onClose,
  onCreate,
  onSubmit,
}) => {
  const [applicantName, setApplicantName] = useState('');
  const [loanAmount, setLoanAmount] = useState('2500000');
  const [loanPurpose, setLoanPurpose] = useState('Home Loan');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = applicantName.trim();
    const amount = parseFloat(loanAmount);

    if (!name) {
      setError('Please enter the applicant full name.');
      return;
    }
    if (isNaN(amount) || amount <= 0) {
      setError('Please enter a valid loan amount.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const handler = onSubmit || onCreate;
      if (handler) {
        await handler({
          applicant_name: name,
          loan_amount: amount,
          loan_purpose: loanPurpose,
        });
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create application');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 select-none">
      <div className="w-full max-w-md rounded-xs bg-theme-card border border-theme-border shadow-2xl overflow-hidden flex flex-col transition-colors duration-200 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-theme-border bg-theme-panel">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-xs bg-theme-brand/10 border border-theme-brand/20 flex items-center justify-center text-theme-brand">
              <UserPlus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-serif font-bold text-theme-primary">
                New Loan Dossier
              </h3>
              <p className="text-[10px] text-theme-muted font-mono uppercase tracking-wider">
                Retail Underwriting Ingestion
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1 rounded-xs text-theme-muted hover:text-theme-primary hover:bg-theme-panel-hover transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {error && (
            <div className="p-2.5 rounded-xs bg-theme-flag-bg border border-theme-flag-border text-theme-flag text-xs">
              {error}
            </div>
          )}

          {/* Applicant Full Name */}
          <div className="space-y-1">
            <label className="font-mono font-bold text-theme-primary flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-theme-muted" />
              <span>Applicant Full Name *</span>
            </label>
            <input
              type="text"
              value={applicantName}
              onChange={(e) => setApplicantName(e.target.value)}
              placeholder="e.g. Rohan Gupta"
              required
              className="w-full bg-theme-panel border border-theme-border rounded-xs px-3 py-2 text-xs font-sans text-theme-primary placeholder-theme-muted focus:outline-none focus:border-theme-brand shadow-2xs"
            />
          </div>

          {/* Loan Amount */}
          <div className="space-y-1">
            <label className="font-mono font-bold text-theme-primary flex items-center gap-1.5">
              <IndianRupee className="w-3.5 h-3.5 text-theme-muted" />
              <span>Requested Loan Amount (INR) *</span>
            </label>
            <input
              type="number"
              value={loanAmount}
              onChange={(e) => setLoanAmount(e.target.value)}
              placeholder="e.g. 2500000"
              min="50000"
              step="50000"
              required
              className="w-full bg-theme-panel border border-theme-border rounded-xs px-3 py-2 text-xs font-mono text-theme-primary placeholder-theme-muted focus:outline-none focus:border-theme-brand shadow-2xs"
            />
          </div>

          {/* Loan Purpose */}
          <div className="space-y-1">
            <label className="font-mono font-bold text-theme-primary flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-theme-muted" />
              <span>Loan Purpose</span>
            </label>
            <select
              value={loanPurpose}
              onChange={(e) => setLoanPurpose(e.target.value)}
              className="w-full bg-theme-panel border border-theme-border rounded-xs px-3 py-2 text-xs font-sans text-theme-primary focus:outline-none focus:border-theme-brand shadow-2xs cursor-pointer"
            >
              <option value="Home Loan">Home Loan (Residential Mortgage)</option>
              <option value="Personal Loan">Personal Loan (Unsecured Credit)</option>
              <option value="Auto Loan">Auto Loan (Vehicle Financing)</option>
              <option value="Education Loan">Education Loan</option>
              <option value="Business Loan">Business Expansion</option>
            </select>
          </div>

          <div className="pt-2 flex items-center justify-end gap-2 border-t border-theme-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-3 py-2 rounded-xs border border-theme-border bg-theme-panel hover:bg-theme-panel-hover text-theme-secondary text-xs font-mono font-semibold transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xs text-xs font-mono font-bold bg-theme-brand hover:opacity-90 text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Creating Dossier...</span>
                </>
              ) : (
                <>
                  <UserPlus className="w-3.5 h-3.5" />
                  <span>Initialize Application</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
