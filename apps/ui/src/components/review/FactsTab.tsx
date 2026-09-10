import React from 'react';
import { LoanApplication } from '../../types/application';
import { EvidenceRef } from '../../types/evidence';
import { formatCurrency } from '../../utils/pii';
import { MaskedValue } from '../common/MaskedValue';
import { ExternalLink, Check, AlertTriangle } from 'lucide-react';

interface FactsTabProps {
  application: LoanApplication;
  onSelectEvidence: (ev: EvidenceRef) => void;
}

export const FactsTab: React.FC<FactsTabProps> = ({ application, onSelectEvidence }) => {
  const payslip = application.payslip_facts;
  const bank = application.bank_facts;
  const tax = application.tax_facts;

  // Stated vs verified variance calculation for display
  const statedNet = payslip?.net_salary?.amount || 0;
  const verifiedCredit = bank?.average_salary_credit?.amount || bank?.salary_credits?.[0]?.amount || 0;
  const variance = statedNet > 0 ? ((verifiedCredit - statedNet) / statedNet) * 100 : 0;
  const isVarianceAcceptable = Math.abs(variance) <= 5.0;

  return (
    <div className="space-y-4">
      {/* Financial Reconciliation Summary Matrix */}
      <div className="p-3.5 rounded bg-white border border-[#E3DDD3] shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-[#E3DDD3] pb-2">
          <span className="text-xs font-serif font-bold text-stone-900 uppercase tracking-wider">
            Payroll Reconciliation Audit
          </span>
          <span
            className={`inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded border ${
              isVarianceAcceptable
                ? 'bg-[#F0FDF4] border-[#15803D] text-[#14532D]'
                : 'bg-[#FEF2F2] border-[#DC2626] text-[#991B1B]'
            }`}
          >
            {isVarianceAcceptable ? (
              <Check className="w-3 h-3 text-[#15803D]" />
            ) : (
              <AlertTriangle className="w-3 h-3 text-[#DC2626]" />
            )}
            <span>Variance: {variance >= 0 ? `+${variance.toFixed(2)}%` : `${variance.toFixed(2)}%`}</span>
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-2.5 rounded bg-[#FBF9F5] border border-[#E3DDD3]">
            <span className="text-[10px] text-stone-500 block mb-1 uppercase font-mono font-semibold">
              Stated Payslip Net Salary
            </span>
            <span className="text-sm font-mono font-bold text-stone-900 block">
              {formatCurrency(statedNet)}
            </span>
            {payslip?.net_salary?.source && (
              <button
                type="button"
                onClick={() => onSelectEvidence(payslip.net_salary!.source)}
                className="mt-2 text-[10px] text-[#92400E] hover:text-stone-900 flex items-center gap-1 font-mono cursor-pointer font-medium"
              >
                <span>View Citation</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </button>
            )}
          </div>

          <div className="p-2.5 rounded bg-[#FBF9F5] border border-[#E3DDD3]">
            <span className="text-[10px] text-stone-500 block mb-1 uppercase font-mono font-semibold">
              Verified Bank Deposit
            </span>
            <span
              className={`text-sm font-mono font-bold block ${
                isVarianceAcceptable ? 'text-[#14532D]' : 'text-[#991B1B]'
              }`}
            >
              {formatCurrency(verifiedCredit)}
            </span>
            {bank?.salary_credits?.[0]?.source && (
              <button
                type="button"
                onClick={() => onSelectEvidence(bank.salary_credits[0].source)}
                className="mt-2 text-[10px] text-[#92400E] hover:text-stone-900 flex items-center gap-1 font-mono cursor-pointer font-medium"
              >
                <span>View Citation</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Structured Domain Facts Details */}
      <div className="space-y-3">
        {/* Banking Profile */}
        <div className="p-3.5 rounded bg-white border border-[#E3DDD3] shadow-sm text-xs space-y-2">
          <h4 className="font-serif font-bold text-stone-900 text-xs border-b border-[#E3DDD3] pb-1.5 flex justify-between items-center">
            <span>Banking Verification</span>
            <span className="text-[10px] text-stone-500 font-mono">
              {bank?.bank_name || 'Bank Record'}
            </span>
          </h4>

          <div className="flex justify-between items-center text-stone-700">
            <span className="text-stone-500">Account Holder:</span>
            <span className="font-medium text-stone-900">{bank?.account_holder || '—'}</span>
          </div>

          <div className="flex justify-between items-center text-stone-700">
            <span className="text-stone-500">Masked Account:</span>
            <MaskedValue value={bank?.account_number_masked} type="account" />
          </div>

          <div className="flex justify-between items-center text-stone-700">
            <span className="text-stone-500">Closing Balance:</span>
            <span className="font-mono font-semibold text-stone-900">
              {formatCurrency(bank?.closing_balance?.amount)}
            </span>
          </div>

          <div className="flex justify-between items-center text-stone-700">
            <span className="text-stone-500">Cheque / ECS Bounces:</span>
            <span
              className={`font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${
                bank?.bounced_transactions === 0
                  ? 'bg-[#F0FDF4] text-[#14532D] border border-[#BBF7D0]'
                  : 'bg-[#FEF2F2] text-[#991B1B] border border-[#FECACA]'
              }`}
            >
              {bank?.bounced_transactions ?? 0} Inward Bounces
            </span>
          </div>
        </div>

        {/* Tax Filing Facts */}
        <div className="p-3.5 rounded bg-white border border-[#E3DDD3] shadow-sm text-xs space-y-2">
          <h4 className="font-serif font-bold text-stone-900 text-xs border-b border-[#E3DDD3] pb-1.5 flex justify-between items-center">
            <span>ITR-V Tax Return</span>
            <span className="text-[10px] text-stone-500 font-mono">
              AY {tax?.assessment_year || '2026-27'}
            </span>
          </h4>

          <div className="flex justify-between items-center text-stone-700">
            <span className="text-stone-500">Assessee Name:</span>
            <span className="font-medium text-stone-900">{tax?.assessee_name || '—'}</span>
          </div>

          <div className="flex justify-between items-center text-stone-700">
            <span className="text-stone-500">Assessee PAN:</span>
            <MaskedValue value={tax?.pan_number} type="pan" />
          </div>

          <div className="flex justify-between items-center text-stone-700">
            <span className="text-stone-500">Gross Total Income:</span>
            <span className="font-mono font-bold text-[#14532D]">
              {formatCurrency(tax?.gross_total_income?.amount)}
            </span>
          </div>

          <div className="flex justify-between items-center text-stone-700">
            <span className="text-stone-500">Total Tax Paid:</span>
            <span className="font-mono font-medium text-stone-900">
              {formatCurrency(tax?.total_tax_paid?.amount)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
