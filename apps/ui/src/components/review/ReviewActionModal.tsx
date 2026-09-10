import React, { useState, useEffect } from 'react';
import { ReviewDecision } from '../../types/api';
import { useAuth } from '../../context/AuthContext';
import { CheckCircle2, AlertTriangle, HelpCircle, X, Loader2, Shield } from 'lucide-react';

interface ReviewActionModalProps {
  isOpen: boolean;
  decision: ReviewDecision | null;
  applicationId: string;
  onClose: () => void;
  onSubmit: (notes: string) => Promise<void>;
  isSubmitting: boolean;
}

export const ReviewActionModal: React.FC<ReviewActionModalProps> = ({
  isOpen,
  decision,
  applicationId,
  onClose,
  onSubmit,
  isSubmitting,
}) => {
  const { user } = useAuth();
  const [notes, setNotes] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Reset modal state whenever a different decision (or dossier) is opened
  useEffect(() => {
    setNotes('');
    setConfirmText('');
    setError(null);
  }, [decision, applicationId, isOpen]);

  if (!isOpen || !decision) return null;

  const getDecisionMeta = () => {
    const reviewer = user?.name ? ` by ${user.name}` : '';
    switch (decision) {
      case 'APPROVED':
        return {
          title: 'Sign Off & Approve Application',
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />,
          btnBg: 'bg-emerald-700 hover:bg-emerald-600 text-white',
          desc: 'Confirm that all deterministic verification findings meet credit underwriting standards. This action advances state to REVIEWED.',
          consequence: `Records APPROVED${reviewer} in the immutable audit trail. State transitions to REVIEWED and the thread is sealed.`,
        };
      case 'REJECTED':
        return {
          title: 'Flag Discrepancy & Reject Application',
          icon: <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />,
          btnBg: 'bg-rose-700 hover:bg-rose-600 text-white',
          desc: 'Flag severe discrepancy (e.g. income inflation, KYC mismatch). Rejection rationale is mandatory for the audit log.',
          consequence: `Records REJECTED${reviewer} in the immutable audit trail. State transitions to REVIEWED and the thread is sealed.`,
        };
      case 'NEEDS_INFO':
        return {
          title: 'Request Supplemental Information',
          icon: <HelpCircle className="w-5 h-5 text-amber-600 dark:text-amber-400" />,
          btnBg: 'bg-amber-700 hover:bg-amber-600 text-white',
          desc: 'Request additional documentation from applicant or branch manager. State transitions to NEEDS_INFORMATION.',
          consequence: `Records NEEDS_INFO${reviewer} in the immutable audit trail. State transitions to NEEDS_INFORMATION for follow-up.`,
        };
    }
  };

  const meta = getDecisionMeta();
  const confirmMatches = confirmText.trim() === applicationId;

  const handleConfirm = async () => {
    if (!confirmMatches) {
      setError(`Type the application ID (${applicationId}) to confirm this decision.`);
      return;
    }
    if ((decision === 'REJECTED' || decision === 'NEEDS_INFO') && notes.trim().length < 5) {
      setError('Please provide a substantive audit rationale (min 5 characters).');
      return;
    }
    setError(null);
    await onSubmit(notes);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4 select-none">
      <div className="w-full max-w-md rounded-xs bg-theme-card border border-theme-border shadow-2xl overflow-hidden flex flex-col transition-colors duration-200">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-theme-border bg-theme-panel">
          <div className="flex items-center gap-2.5">
            {meta.icon}
            <h3 className="text-sm font-serif font-bold text-theme-primary">{meta.title}</h3>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1 rounded-xs text-theme-muted hover:text-theme-primary hover:bg-theme-panel-hover transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 text-xs">
          <div className="p-3 rounded-xs bg-theme-panel border border-theme-border text-theme-secondary leading-relaxed">
            <p className="font-medium">{meta.desc}</p>
          </div>

          {/* Rationale Input */}
          <div className="space-y-1.5">
            <label className="font-mono font-bold text-theme-primary block">
              Underwriter Audit Rationale{' '}
              {decision === 'APPROVED' ? (
                <span className="text-theme-muted font-normal">(Optional)</span>
              ) : (
                <span className="text-theme-flag font-bold">*</span>
              )}
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={
                decision === 'APPROVED'
                  ? 'E.g., Stated income verified via bank payroll credits, debt-service capacity adequate...'
                  : decision === 'REJECTED'
                    ? 'E.g., Payroll credit mismatch (-27%) exceeds policy threshold; uncorroborated salary...'
                    : 'E.g., Requesting Form 16 / appointment letter to clarify employer entity name difference...'
              }
              className="w-full p-2.5 rounded-xs bg-theme-panel border border-theme-border text-theme-primary placeholder-theme-muted focus:outline-none focus:border-theme-brand font-sans leading-relaxed text-xs transition-colors"
            />
          </div>

          {/* Friction / Dual-Sign Confirmation Box */}
          <div className="space-y-1.5 p-3 rounded-xs bg-amber-500/10 border border-amber-500/30">
            <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-400 font-mono font-bold text-[11px]">
              <Shield className="w-3.5 h-3.5" />
              <span>Two-Way Authorization Confirmation</span>
            </div>
            <p className="text-[11px] text-theme-secondary leading-relaxed">
              To prevent accidental authorization, please enter the dossier identifier{' '}
              <strong className="font-mono text-theme-primary bg-theme-card px-1 py-0.5 rounded-xs border border-theme-border">
                {applicationId}
              </strong>{' '}
              below:
            </p>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={`Type ${applicationId} to seal`}
              className="w-full mt-1 p-2 rounded-xs bg-theme-card border border-theme-border text-theme-primary placeholder-theme-muted focus:outline-none focus:border-theme-brand font-mono text-xs"
            />
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-2.5 rounded-xs bg-theme-flag-bg border border-theme-flag-border text-theme-flag text-[11px] font-medium animate-fade-in flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Audit Trail Note */}
          <div className="text-[10px] text-theme-muted font-mono leading-relaxed border-t border-theme-border pt-3">
            {meta.consequence}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-theme-border bg-theme-panel flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-3 py-1.5 rounded-xs border border-theme-border bg-theme-card hover:bg-theme-panel text-theme-secondary hover:text-theme-primary text-xs font-mono transition-colors cursor-pointer disabled:opacity-50"
          >
            Cancel [Esc]
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting || !confirmMatches}
            className={`px-4 py-1.5 rounded-xs text-xs font-mono font-bold shadow-sm flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${meta.btnBg}`}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Recording Audit...</span>
              </>
            ) : (
              <span>Confirm & Authorize</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
