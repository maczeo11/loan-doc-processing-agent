import type { LoanApplicationState } from '../types/contracts';

export function downloadJsonExport(state: LoanApplicationState) {
  const exportData = {
    application_id: state.application_id,
    status: state.status,
    applicant: state.applicant,
    payslip: state.payslip,
    bank_statement: state.bank_statement,
    tax_return: state.tax_return,
    findings: state.findings,
    missing_documents: state.missing_documents,
    summary_markdown: state.summary_markdown,
    reviewer_decision: state.reviewer_decision,
    reviewer_notes: state.reviewer_notes,
    corrections_applied: state.corrections_applied,
    exported_at: new Date().toISOString(),
  };

  const blob = new Blob([JSON.stringify(exportData, null, 2)], {
    type: 'application/json',
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = `${state.application_id}-review-export.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}
