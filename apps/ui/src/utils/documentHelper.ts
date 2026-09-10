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
    default:
      if (docType) {
        return docType
          .split('_')
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');
      }
      return docId;
  }
}

export function getDocumentCategory(docType?: string): string {
  switch (docType) {
    case 'payslip':
      return 'Salary Payslip';
    case 'bank_statement':
      return 'Bank Account';
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
