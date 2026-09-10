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

  // Display-only reference figures. The PASS/FLAG/UNKNOWN verdict is NEVER
  // computed here — it is rendered verbatim from the backend RULE-INC-01
  // Finding (Prime Invariant: deterministic code decides).
  const statedNet = payslip?.net_salary?.amount || 0;
  const verifiedCredit = bank?.average_salary_credit?.amount || bank?.salary_credits?.[0]?.amount || 0;
  const incFinding = application.findings.find((f) => f.rule_id === 'RULE-INC-01');
  const incVerdict = incFinding?.verdict ?? 'unknown';

  return (
    <div className="space-y-4">
      {/* Financial Reconciliation Summary Matrix */}
      <div className="p-3.5 rounded-xs bg-theme-panel border border-theme-border shadow-xs space-y-3">
        <div className="flex items-center justify-between border-b border-theme-border pb-2">
          <span className="text-xs font-serif font-bold text-theme-primary uppercase tracking-wider">
            Payroll Reconciliation Audit
          </span>
          <span
            className={`inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded-xs border ${
              incVerdict === 'pass'
                ? 'bg-theme-pass-bg border-theme-pass-border text-theme-pass'
                : incVerdict === 'flag'
                  ? 'bg-theme-flag-bg border-theme-flag-border text-theme-flag'
                  : 'bg-[#FFFBEB] border-[#D97706] text-[#92400E]'
            }`}
            title={incFinding ? `Backend ${incFinding.rule_id}: ${incFinding.reason}` : 'Backend has not issued RULE-INC-01 yet'}
          >
            {incVerdict === 'pass' ? (
              <Check className="w-3 h-3 text-theme-pass" />
            ) : (
              <AlertTriangle className={`w-3 h-3 ${incVerdict === 'flag' ? 'text-theme-flag' : 'text-[#D97706]'}`} />
            )}
            <span>Backend RULE-INC-01: {incVerdict.toUpperCase()}</span>
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-2.5 rounded-xs bg-theme-card border border-theme-border">
            <span className="text-[10px] text-theme-muted block mb-1 uppercase font-mono font-semibold">
              Stated Payslip Net Salary
            </span>
            <span className="text-sm font-mono font-bold text-theme-primary block tabular-nums">
              {formatCurrency(statedNet)}
            </span>
            {payslip?.net_salary?.source && (
              <button
                type="button"
                onClick={() => onSelectEvidence(payslip.net_salary!.source)}
                className="mt-2 text-[10px] text-amber-600 dark:text-amber-400 hover:text-theme-primary flex items-center gap-1 font-mono cursor-pointer font-medium"
              >
                <span>View Citation</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </button>
            )}
          </div>

          <div className="p-2.5 rounded-xs bg-theme-card border border-theme-border">
            <span className="text-[10px] text-theme-muted block mb-1 uppercase font-mono font-semibold">
              Verified Bank Deposit
            </span>
            <span className="text-sm font-mono font-bold block tabular-nums text-theme-primary">
              {formatCurrency(verifiedCredit)}
            </span>
            {bank?.salary_credits?.[0]?.source && (
              <button
                type="button"
                onClick={() => onSelectEvidence(bank.salary_credits[0].source)}
                className="mt-2 text-[10px] text-amber-600 dark:text-amber-400 hover:text-theme-primary flex items-center gap-1 font-mono cursor-pointer font-medium"
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
        <div className="p-3.5 rounded-xs bg-theme-card border border-theme-border shadow-xs text-xs space-y-2">
          <h4 className="font-serif font-bold text-theme-primary text-xs border-b border-theme-border pb-1.5 flex justify-between items-center">
            <span>Banking Verification</span>
            <span className="text-[10px] text-theme-muted font-mono">
              {bank?.bank_name || 'Bank Record'}
            </span>
          </h4>

          <div className="flex justify-between items-center text-theme-secondary">
            <span className="text-theme-muted">Account Holder:</span>
            <span className="font-medium text-theme-primary">{bank?.account_holder || '—'}</span>
          </div>

          <div className="flex justify-between items-center text-theme-secondary">
            <span className="text-theme-muted">Masked Account:</span>
            <MaskedValue value={bank?.account_number_masked} type="account" />
          </div>

          <div className="flex justify-between items-center text-theme-secondary">
            <span className="text-theme-muted">Closing Balance:</span>
            <span className="font-mono font-semibold text-theme-primary tabular-nums">
              {formatCurrency(bank?.closing_balance?.amount)}
            </span>
          </div>

          <div className="flex justify-between items-center text-theme-secondary">
            <span className="text-theme-muted">Cheque / ECS Bounces:</span>
            <span
              className={`font-mono font-semibold px-2 py-0.5 rounded-xs text-[11px] ${
                bank?.bounced_transactions === 0
                  ? 'bg-theme-pass-bg text-theme-pass border border-theme-pass-border'
                  : 'bg-theme-flag-bg text-theme-flag border border-theme-flag-border'
              }`}
            >
              {bank?.bounced_transactions ?? 'UNKNOWN'} Inward Bounces
            </span>
          </div>
        </div>

        {/* Tax Filing Facts */}
        <div className="p-3.5 rounded-xs bg-theme-card border border-theme-border shadow-xs text-xs space-y-2">
          <h4 className="font-serif font-bold text-theme-primary text-xs border-b border-theme-border pb-1.5 flex justify-between items-center">
            <span>ITR-V Tax Return</span>
            <span className="text-[10px] text-theme-muted font-mono">
              AY {tax?.assessment_year || '2024-25'}
            </span>
          </h4>

          <div className="flex justify-between items-center text-theme-secondary">
            <span className="text-theme-muted">Assessee Name:</span>
            <span className="font-medium text-theme-primary">{tax?.assessee_name || '—'}</span>
          </div>

          <div className="flex justify-between items-center text-theme-secondary">
            <span className="text-theme-muted">Assessee PAN:</span>
            <MaskedValue value={tax?.pan_number} type="pan" />
          </div>

          <div className="flex justify-between items-center text-theme-secondary">
            <span className="text-theme-muted">Gross Total Income:</span>
            <span className="font-mono font-bold text-theme-pass tabular-nums">
              {formatCurrency(tax?.gross_total_income?.amount)}
            </span>
          </div>

          <div className="flex justify-between items-center text-theme-secondary">
            <span className="text-theme-muted">Total Tax Paid:</span>
            <span className="font-mono font-medium text-theme-primary tabular-nums">
              {formatCurrency(tax?.total_tax_paid?.amount)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
