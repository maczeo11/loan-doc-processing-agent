import React from 'react';
import { LoanApplication } from '../../types/application';
import { EvidenceRef } from '../../types/evidence';
import { formatCurrency } from '../../utils/pii';
import { MaskedValue } from '../common/MaskedValue';
import { ExternalLink, CheckCircle2, AlertTriangle, Building2, Landmark, FileText, UserCheck, ShieldCheck } from 'lucide-react';

interface FactsTabProps {
  application: LoanApplication;
  onSelectEvidence: (ev: EvidenceRef) => void;
}

export const FactsTab: React.FC<FactsTabProps> = ({ application, onSelectEvidence }) => {
  const payslip = application.payslip_facts;
  const bank = application.bank_facts;
  const tax = application.tax_facts;
  const applicant = application.applicant_facts;

  // Display-only: amounts formatted, verdict comes from backend RULE-INC-01 Finding.
  // No client-side financial math per AGENTS §7 (deterministic code decides).
  const statedNet = payslip?.net_salary?.amount || 0;
  const verifiedCredit = bank?.average_salary_credit?.amount || bank?.salary_credits?.[0]?.amount || 0;
  const salaryFinding = (application.findings || []).find((f) => f.rule_id === 'RULE-INC-01');
  const salaryVerdict = salaryFinding?.verdict || 'unknown';
  const isVarianceAcceptable = salaryVerdict === 'pass';

  const hasAnyFacts = !!(payslip || bank || tax || applicant?.full_name);

  if (!hasAnyFacts) {
    return (
      <div className="p-8 text-center border border-dashed border-theme-border rounded-xs bg-theme-panel/30 my-4">
        <Landmark className="w-10 h-10 text-theme-muted mx-auto mb-2 opacity-50" />
        <h4 className="text-xs font-serif font-bold text-theme-primary mb-1">
          Financial Facts Ledger Empty
        </h4>
        <p className="text-[11px] text-theme-muted leading-relaxed max-w-xs mx-auto">
          Deterministic entity extractors populate this verified ledger once the LangGraph pipeline executes on uploaded dossier PDFs.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 font-sans">
      {/* Top Banner: Double-Entry Reconciliation Ledger Card */}
      <div className="rounded-xs bg-theme-panel border border-theme-border shadow-xs overflow-hidden">
        <div className="px-3.5 py-2.5 bg-theme-card border-b border-theme-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-xs bg-theme-brand/10 text-theme-brand flex items-center justify-center">
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
            <span className="text-xs font-serif font-bold text-theme-primary uppercase tracking-wider">
              Cross-Document Reconciliation Ledger
            </span>
          </div>
          <span
            className={`inline-flex items-center gap-1 text-[11px] font-mono font-bold px-2 py-0.5 rounded-xs border ${
              statedNet > 0 && isVarianceAcceptable
                ? 'bg-theme-pass-bg border-theme-pass-border text-theme-pass'
                : statedNet > 0
                ? 'bg-theme-flag-bg border-theme-flag-border text-theme-flag'
                : 'bg-theme-unknown-bg border-theme-unknown-border text-theme-unknown'
            }`}
          >
            {statedNet > 0 && isVarianceAcceptable ? (
              <CheckCircle2 className="w-3 h-3 text-theme-pass" />
            ) : (
              <AlertTriangle className="w-3 h-3 text-theme-flag" />
            )}
            <span>
              {salaryFinding
                ? `Backend verdict: ${salaryVerdict.toUpperCase()} (${salaryFinding.rule_id})`
                : 'Pending Reconciliation'}
            </span>
          </span>
        </div>

        {/* Ledger Balance Sheet Style Comparison */}
        <div className="p-3 grid grid-cols-2 gap-3 text-xs bg-theme-panel">
          {/* Stated Payslip */}
          <div className="p-3 rounded-xs bg-theme-card border border-theme-border flex flex-col justify-between">
            <div>
              <span className="text-[10px] text-theme-muted uppercase font-mono font-bold tracking-wider block mb-1">
                Payslip Stated (Net)
              </span>
              <div className="text-base font-mono font-bold text-theme-primary tabular-nums tracking-tight">
                {statedNet > 0 ? formatCurrency(statedNet) : '—'}
              </div>
              <p className="text-[10px] text-theme-muted mt-0.5">
                {payslip?.employer_name ? `Employer: ${payslip.employer_name}` : 'Monthly payroll voucher'}
              </p>
            </div>
            {payslip?.net_salary?.source && (
              <button
                type="button"
                onClick={() => onSelectEvidence(payslip.net_salary!.source)}
                className="mt-2.5 pt-2 border-t border-theme-border/60 text-[10px] text-theme-brand hover:underline flex items-center justify-between font-mono cursor-pointer font-semibold"
              >
                <span>Doc Citation ({payslip.net_salary.source.document_id})</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Verified Bank Deposit */}
          <div className="p-3 rounded-xs bg-theme-card border border-theme-border flex flex-col justify-between">
            <div>
              <span className="text-[10px] text-theme-muted uppercase font-mono font-bold tracking-wider block mb-1">
                Bank Credit (Actual)
              </span>
              <div
                className={`text-base font-mono font-bold tabular-nums tracking-tight ${
                  statedNet > 0 && isVarianceAcceptable ? 'text-theme-pass' : 'text-theme-flag'
                }`}
              >
                {verifiedCredit > 0 ? formatCurrency(verifiedCredit) : '—'}
              </div>
              <p className="text-[10px] text-theme-muted mt-0.5">
                {bank?.bank_name ? `Bank: ${bank.bank_name}` : 'Verified inward payroll deposit'}
              </p>
            </div>
            {bank?.salary_credits?.[0]?.source && (
              <button
                type="button"
                onClick={() => onSelectEvidence(bank.salary_credits[0].source)}
                className="mt-2.5 pt-2 border-t border-theme-border/60 text-[10px] text-theme-brand hover:underline flex items-center justify-between font-mono cursor-pointer font-semibold"
              >
                <span>Doc Citation ({bank.salary_credits[0].source.document_id})</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Institutional Table Ledger: Extracted Facts */}
      <div className="rounded-xs bg-theme-card border border-theme-border shadow-xs overflow-hidden">
        <div className="px-3.5 py-2 bg-theme-panel border-b border-theme-border flex items-center justify-between text-xs">
          <span className="font-serif font-bold text-theme-primary flex items-center gap-1.5">
            <Landmark className="w-3.5 h-3.5 text-theme-muted" />
            <span>Institutional Entity Ledger</span>
          </span>
          <span className="text-[10px] font-mono text-theme-muted">Pure Deterministic Extraction</span>
        </div>

        <table className="w-full text-left text-xs border-collapse font-sans">
          <thead>
            <tr className="border-b border-theme-border bg-theme-panel/40 text-[10px] font-mono uppercase tracking-wider text-theme-muted">
              <th className="py-2 px-3 font-semibold">Ledger Item</th>
              <th className="py-2 px-3 font-semibold">Extracted Value</th>
              <th className="py-2 px-3 font-semibold text-right">Provenance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-theme-border text-xs">
            {/* Applicant Name */}
            <tr className="hover:bg-theme-panel/50 transition-colors">
              <td className="py-2.5 px-3 text-theme-muted font-medium flex items-center gap-1.5">
                <UserCheck className="w-3 h-3 text-theme-muted" />
                <span>Applicant Name</span>
              </td>
              <td className="py-2.5 px-3 font-serif font-bold text-theme-primary">
                {applicant?.full_name || '—'}
              </td>
              <td className="py-2.5 px-3 text-right">
                {applicant?.source_name ? (
                  <button
                    type="button"
                    onClick={() => onSelectEvidence(applicant.source_name!)}
                    className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-theme-brand hover:underline"
                  >
                    <span>P.{applicant.source_name.page_number}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                ) : (
                  <span className="text-[10px] font-mono text-theme-muted">—</span>
                )}
              </td>
            </tr>

            {/* KYC Permanent Account Number */}
            <tr className="hover:bg-theme-panel/50 transition-colors">
              <td className="py-2.5 px-3 text-theme-muted font-medium flex items-center gap-1.5">
                <ShieldCheck className="w-3 h-3 text-theme-muted" />
                <span>KYC PAN</span>
              </td>
              <td className="py-2.5 px-3 font-mono font-bold text-theme-primary">
                <MaskedValue value={applicant?.pan_number} type="pan" />
              </td>
              <td className="py-2.5 px-3 text-right">
                {applicant?.source_pan ? (
                  <button
                    type="button"
                    onClick={() => onSelectEvidence(applicant.source_pan!)}
                    className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-theme-brand hover:underline"
                  >
                    <span>P.{applicant.source_pan.page_number}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                ) : (
                  <span className="text-[10px] font-mono text-theme-muted">—</span>
                )}
              </td>
            </tr>

            {/* Employer / Company */}
            <tr className="hover:bg-theme-panel/50 transition-colors">
              <td className="py-2.5 px-3 text-theme-muted font-medium flex items-center gap-1.5">
                <Building2 className="w-3 h-3 text-theme-muted" />
                <span>Employer</span>
              </td>
              <td className="py-2.5 px-3 font-medium text-theme-primary">
                {payslip?.employer_name || '—'}
              </td>
              <td className="py-2.5 px-3 text-right">
                {payslip?.gross_salary?.source ? (
                  <button
                    type="button"
                    onClick={() => onSelectEvidence(payslip.gross_salary!.source)}
                    className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-theme-brand hover:underline"
                  >
                    <span>P.{payslip.gross_salary.source.page_number}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                ) : (
                  <span className="text-[10px] font-mono text-theme-muted">—</span>
                )}
              </td>
            </tr>

            {/* Bank Account Number */}
            <tr className="hover:bg-theme-panel/50 transition-colors">
              <td className="py-2.5 px-3 text-theme-muted font-medium flex items-center gap-1.5">
                <Landmark className="w-3 h-3 text-theme-muted" />
                <span>Bank Account</span>
              </td>
              <td className="py-2.5 px-3 font-mono text-theme-primary">
                <MaskedValue value={bank?.account_number_masked} type="account" />
                {bank?.bank_name && (
                  <span className="ml-1.5 text-[10px] text-theme-muted font-sans">({bank.bank_name})</span>
                )}
              </td>
              <td className="py-2.5 px-3 text-right">
                {bank?.salary_credits?.[0]?.source ? (
                  <button
                    type="button"
                    onClick={() => onSelectEvidence(bank.salary_credits[0].source)}
                    className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-theme-brand hover:underline"
                  >
                    <span>P.{bank.salary_credits[0].source.page_number}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                ) : (
                  <span className="text-[10px] font-mono text-theme-muted">—</span>
                )}
              </td>
            </tr>

            {/* Bank Closing Balance */}
            <tr className="hover:bg-theme-panel/50 transition-colors">
              <td className="py-2.5 px-3 text-theme-muted font-medium flex items-center gap-1.5">
                <Landmark className="w-3 h-3 text-theme-muted" />
                <span>Closing Balance</span>
              </td>
              <td className="py-2.5 px-3 font-mono font-semibold text-theme-primary tabular-nums">
                {bank?.closing_balance?.amount ? formatCurrency(bank.closing_balance.amount) : '—'}
              </td>
              <td className="py-2.5 px-3 text-right">
                {bank?.closing_balance?.source ? (
                  <button
                    type="button"
                    onClick={() => onSelectEvidence(bank.closing_balance!.source)}
                    className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-theme-brand hover:underline"
                  >
                    <span>P.{bank.closing_balance.source.page_number}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                ) : (
                  <span className="text-[10px] font-mono text-theme-muted">—</span>
                )}
              </td>
            </tr>

            {/* Inward ECS / Cheque Bounces */}
            <tr className="hover:bg-theme-panel/50 transition-colors">
              <td className="py-2.5 px-3 text-theme-muted font-medium flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3 text-theme-muted" />
                <span>ECS / Inward Bounces</span>
              </td>
              <td className="py-2.5 px-3 font-mono">
                <span
                  className={`px-1.5 py-0.5 rounded-xs font-bold text-[10px] border ${
                    bank?.bounced_transactions === 0
                      ? 'bg-theme-pass-bg text-theme-pass border-theme-pass-border'
                      : 'bg-theme-flag-bg text-theme-flag border-theme-flag-border'
                  }`}
                >
                  {bank?.bounced_transactions ?? 0} Bounces
                </span>
              </td>
              <td className="py-2.5 px-3 text-right">
                <span className="text-[10px] font-mono text-theme-muted">Statement</span>
              </td>
            </tr>

            {/* ITR Gross Total Income */}
            <tr className="hover:bg-theme-panel/50 transition-colors">
              <td className="py-2.5 px-3 text-theme-muted font-medium flex items-center gap-1.5">
                <FileText className="w-3 h-3 text-theme-muted" />
                <span>ITR Gross Income</span>
              </td>
              <td className="py-2.5 px-3 font-mono font-bold text-theme-pass tabular-nums">
                {tax?.gross_total_income?.amount ? formatCurrency(tax.gross_total_income.amount) : '—'}
                {tax?.assessment_year && (
                  <span className="ml-1.5 text-[10px] text-theme-muted font-mono font-normal">
                    (AY {tax.assessment_year})
                  </span>
                )}
              </td>
              <td className="py-2.5 px-3 text-right">
                {tax?.gross_total_income?.source ? (
                  <button
                    type="button"
                    onClick={() => onSelectEvidence(tax.gross_total_income!.source)}
                    className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-theme-brand hover:underline"
                  >
                    <span>P.{tax.gross_total_income.source.page_number}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                ) : (
                  <span className="text-[10px] font-mono text-theme-muted">—</span>
                )}
              </td>
            </tr>

            {/* ITR Total Tax Paid */}
            <tr className="hover:bg-theme-panel/50 transition-colors">
              <td className="py-2.5 px-3 text-theme-muted font-medium flex items-center gap-1.5">
                <FileText className="w-3 h-3 text-theme-muted" />
                <span>ITR Tax Paid</span>
              </td>
              <td className="py-2.5 px-3 font-mono font-medium text-theme-primary tabular-nums">
                {tax?.total_tax_paid?.amount ? formatCurrency(tax.total_tax_paid.amount) : '—'}
              </td>
              <td className="py-2.5 px-3 text-right">
                {tax?.total_tax_paid?.source ? (
                  <button
                    type="button"
                    onClick={() => onSelectEvidence(tax.total_tax_paid!.source)}
                    className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-theme-brand hover:underline"
                  >
                    <span>P.{tax.total_tax_paid.source.page_number}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                ) : (
                  <span className="text-[10px] font-mono text-theme-muted">—</span>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

