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
          icon: <CheckCircle2 className="w-5 h-5 text-[#14532D]" />,
          btnBg: 'bg-[#14532D] hover:bg-[#0F4023] text-white',
          desc: 'Confirm that all deterministic verification findings meet credit underwriting standards. This action advances state to REVIEWED.',
          consequence: `Records APPROVED${reviewer} in the immutable audit trail. State transitions to REVIEWED and the thread is sealed.`,
        };
      case 'REJECTED':
        return {
          title: 'Flag Discrepancy & Reject Application',
          icon: <AlertTriangle className="w-5 h-5 text-[#991B1B]" />,
          btnBg: 'bg-[#991B1B] hover:bg-[#7F1D1D] text-white',
          desc: 'Flag severe discrepancy (e.g. income inflation, KYC mismatch). Rejection rationale is mandatory for the audit log.',
          consequence: `Records REJECTED${reviewer} in the immutable audit trail. State transitions to REVIEWED and the thread is sealed.`,
        };
      case 'NEEDS_INFO':
        return {
          title: 'Request Supplemental Information',
          icon: <HelpCircle className="w-5 h-5 text-[#92400E]" />,
          btnBg: 'bg-white border border-[#B45309] text-[#92400E] hover:bg-[#FFFBEB]',
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 backdrop-blur-xs p-4 select-none">
      <div className="w-full max-w-md rounded-lg bg-white border border-[#E3DDD3] shadow-xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#E3DDD3] bg-[#FBF9F5]">
          <div className="flex items-center gap-2.5">
            {meta.icon}
            <h3 className="text-sm font-serif font-bold text-stone-900">{meta.title}</h3>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1 rounded text-stone-500 hover:text-stone-900 hover:bg-stone-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4">
          <p className="text-xs text-stone-600 leading-relaxed">{meta.desc}</p>

          <div className="p-2.5 rounded bg-[#FBF9F5] border border-[#E3DDD3] text-xs font-mono text-stone-600 flex items-center justify-between">
            <span>Dossier Target:</span>
            <span className="text-[#92400E] font-bold">{applicationId}</span>
          </div>

          <div className="p-2.5 rounded bg-[#FBF9F5] border border-[#E3DDD3] text-xs font-mono text-stone-600 flex items-center justify-between">
            <span>Reviewer Identity:</span>
            <span className="text-stone-900 font-medium">
              {user?.name} ({user?.role})
            </span>
          </div>

          {/* Notes Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-stone-700 flex justify-between">
              <span>Underwriter Audit Rationale</span>
              {(decision === 'REJECTED' || decision === 'NEEDS_INFO') && (
                <span className="text-red-600 text-[11px] font-semibold">Mandatory</span>
              )}
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={
                decision === 'APPROVED'
                  ? 'Optional underwriter notes or approval conditions...'
                  : 'Specify discrepancy details or missing documentation...'
              }
              rows={3}
              className="w-full bg-white border border-[#E3DDD3] rounded-md p-2.5 text-xs text-stone-900 placeholder-stone-400 focus:outline-none focus:border-stone-800 transition-colors shadow-xs"
            />
            {error && <p className="text-[11px] text-red-600">{error}</p>}
          </div>

          {/* Typed confirmation: deliberate friction for high-stakes sign-off */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-stone-700">
              Type <code className="font-mono font-bold text-stone-900">{applicationId}</code> to confirm
            </label>
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={applicationId}
              autoComplete="off"
              className="w-full bg-white border border-[#E3DDD3] rounded-md p-2.5 text-xs font-mono text-stone-900 placeholder-stone-300 focus:outline-none focus:border-stone-800 transition-colors shadow-xs"
            />
          </div>

          <div className="flex items-center gap-1.5 text-[10px] text-stone-500 font-mono">
            <Shield className="w-3 h-3 text-stone-400" />
            <span>HITL Protocol: Resumes LangGraph thread & records immutable audit event.</span>
          </div>
          <p className="text-[11px] text-stone-700 leading-relaxed border-l-2 border-[#B45309] pl-2.5">
            {meta.consequence}
          </p>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-[#E3DDD3] bg-[#FBF9F5] flex justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-3 py-1.5 rounded text-xs font-medium bg-stone-200 hover:bg-stone-300 text-stone-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting || !confirmMatches}
            className={`px-4 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm border ${meta.btnBg} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            <span>Confirm Decision</span>
          </button>
        </div>
      </div>
    </div>
  );
};
