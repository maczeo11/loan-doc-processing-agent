/**
 * Utility functions to map document identifiers and types to human-readable titles and categories.
 */

export function getDocumentTitle(docId: string, docType?: string): string {
  switch (docId) {
    case 'doc-app-form':
      return 'Loan Application Form';
    case 'doc-payslip-jun':
      return 'Payslip (Month 1 - June)';
    case 'doc-payslip-jul':
      return 'Payslip (Month 2 - July)';
    case 'doc-payslip-aug':
      return 'Payslip (Month 3 - August)';
    case 'doc-bank-stmt':
      return 'Bank Statement (6 Months)';
    case 'doc-itr-v':
      return 'ITR-V Acknowledgement (AY 24-25)';
    case 'doc-pan-card':
      return 'PAN Card Identity Proof';
  }

  if (docType && docType !== 'document' && docType !== 'unknown') {
    const category = getDocumentCategory(docType);
    return `${category} • ${docId}`;
  }
  return docId;
}

export function getDocumentCategory(docType?: string): string {
  switch (docType) {
    case 'payslip':
      return 'Salary Payslip';
    case 'bank_statement':
      return 'Bank Account';
    // `tax_acknowledgement` is the pipeline's canonical type; `tax_return` is
    // kept only so older persisted dossiers still render a readable label.
    case 'tax_acknowledgement':
    case 'tax_return':
      return 'Tax Return';
    case 'id_card':
      return 'KYC Proof';
    case 'application_form':
      return 'Application Form';
    default:
      return docType ? docType.replace(/_/g, ' ').toUpperCase() : 'General Document';
  }
}
