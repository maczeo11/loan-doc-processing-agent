import React, { useState } from 'react';
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
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !decision) return null;

  const getDecisionMeta = () => {
    switch (decision) {
      case 'APPROVED':
        return {
          title: 'Sign Off & Approve Application',
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
          colorClass: 'text-emerald-300',
          btnBg: 'bg-emerald-600 hover:bg-emerald-500 text-white',
          desc: 'Confirm that all deterministic verification findings meet credit underwriting standards. This action advances state to REVIEWED.',
        };
      case 'REJECTED':
        return {
          title: 'Flag Discrepancy & Reject Application',
          icon: <AlertTriangle className="w-5 h-5 text-rose-400" />,
          colorClass: 'text-rose-300',
          btnBg: 'bg-rose-600 hover:bg-rose-500 text-white',
          desc: 'Flag severe discrepancy (e.g. income inflation, KYC mismatch). Rejection rationale is mandatory for the audit log.',
        };
      case 'NEEDS_INFO':
        return {
          title: 'Request Supplemental Information',
          icon: <HelpCircle className="w-5 h-5 text-amber-400" />,
          colorClass: 'text-amber-300',
          btnBg: 'bg-amber-600 hover:bg-amber-500 text-white',
          desc: 'Request additional documentation from applicant or branch manager. State transitions to NEEDS_INFORMATION.',
        };
    }
  };

  const meta = getDecisionMeta();

  const handleConfirm = async () => {
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

          <div className="flex items-center gap-1.5 text-[10px] text-stone-500 font-mono">
            <Shield className="w-3 h-3 text-stone-400" />
            <span>HITL Protocol: Resumes LangGraph thread & records immutable audit event.</span>
          </div>
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
            disabled={isSubmitting}
            className={`px-4 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm ${meta.btnBg} disabled:opacity-50`}
          >
            {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            <span>Confirm Decision</span>
          </button>
        </div>
      </div>
    </div>
  );
};
