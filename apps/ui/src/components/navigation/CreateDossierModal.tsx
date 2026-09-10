import React, { useState } from 'react';
import { X, FolderPlus, Loader2 } from 'lucide-react';

interface CreateDossierModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (values: { applicant_name: string; loan_amount: number; loan_purpose?: string }) => Promise<void>;
}

export const CreateDossierModal: React.FC<CreateDossierModalProps> = ({
  isOpen,
  onClose,
  onCreate,
}) => {
  const [applicantName, setApplicantName] = useState('');
  const [loanAmount, setLoanAmount] = useState('');
  const [loanPurpose, setLoanPurpose] = useState('Home loan');
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = Number(loanAmount);
    if (!applicantName.trim()) {
      setError('Applicant name is required.');
      return;
    }
    if (!Number.isFinite(amount) || amount <= 0) {
      setError('Loan amount must be a positive number.');
      return;
    }
    setError(null);
    setIsCreating(true);
    try {
      await onCreate({
        applicant_name: applicantName.trim(),
        loan_amount: amount,
        loan_purpose: loanPurpose.trim() || undefined,
      });
      setApplicantName('');
      setLoanAmount('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create dossier');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FolderPlus className="w-5 h-5 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900">New application dossier</h3>
          </div>
          <button
            onClick={onClose}
            disabled={isCreating}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Applicant full name
            </label>
            <input
              value={applicantName}
              onChange={(e) => setApplicantName(e.target.value)}
              placeholder="e.g. Ananya Sharma"
              autoComplete="off"
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Loan amount (INR)
            </label>
            <input
              value={loanAmount}
              onChange={(e) => setLoanAmount(e.target.value)}
              placeholder="e.g. 3500000"
              inputMode="decimal"
              autoComplete="off"
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-400 focus:outline-none font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Purpose (optional)
            </label>
            <input
              value={loanPurpose}
              onChange={(e) => setLoanPurpose(e.target.value)}
              placeholder="e.g. Home loan"
              autoComplete="off"
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-400 focus:outline-none"
            />
          </div>

          {error && (
            <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isCreating}
              className="px-3 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5"
            >
              {isCreating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>Create dossier</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
