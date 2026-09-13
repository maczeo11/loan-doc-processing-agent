/**
 * Deterministic generator for synthetic demo PDF documents in APP-25195.
 * Creates standard PDF 1.4 byte arrays client-side without external dependencies.
 * Strictly adheres to AGENTS.md synthetic watermarking rules.
 */

interface PageLine {
  text: string;
  size?: number;
  isBold?: boolean;
  dx?: number;
  dy?: number;
}

function escapePdfText(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
}

function buildPdf(pages: PageLine[][]): Uint8Array {
  const objects: string[] = [];
  const addObject = (content: string) => {
    objects.push(content);
    return objects.length;
  };

  // Object 1: Catalog
  addObject('<< /Type /Catalog /Pages 2 0 R >>');

  // Object 2: Pages (placeholder)
  const pagesObjIndex = 1;
  objects.push('');

  // Object 3: Helvetica Regular
  addObject('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>');
  // Object 4: Helvetica Bold
  addObject('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>');

  const pageObjRefs: string[] = [];

  for (let p = 0; p < pages.length; p++) {
    const lines = pages[p];
    const streamCommands: string[] = [
      'BT',
      // Watermark header
      '/F2 10 Tf',
      '0.7 0.2 0.2 rg', // Reddish watermark
      '180 810 Td',
      '(SYNTHETIC DEMO - NOT VALID) Tj',
      '0 0 0 rg', // Reset color to black
      '0 -30 Td',
    ];

    let currentY = 780;
    for (const line of lines) {
      const fontSize = line.size || 11;
      const fontRef = line.isBold ? '/F2' : '/F1';
      const text = escapePdfText(line.text);
      const dy = line.dy !== undefined ? line.dy : -20;
      currentY += dy;

      streamCommands.push(`${fontRef} ${fontSize} Tf`);
      streamCommands.push(`0 ${dy} Td`);
      streamCommands.push(`(${text}) Tj`);
    }

    // Page footer
    streamCommands.push('/F1 9 Tf');
    streamCommands.push('0.5 0.5 0.5 rg');
    streamCommands.push(`0 -40 Td`);
    streamCommands.push(`(FinScan AI Dossier Verification - Page ${p + 1} of ${pages.length}) Tj`);
    streamCommands.push('ET');

    const streamBody = streamCommands.join('\n');
    const streamId = addObject(`<< /Length ${streamBody.length} >>\nstream\n${streamBody}\nendstream`);
    const pageId = addObject(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${streamId} 0 R >>`
    );
    pageObjRefs.push(`${pageId} 0 R`);
  }

  // Finalize Object 2: Pages
  objects[pagesObjIndex] = `<< /Type /Pages /Kids [${pageObjRefs.join(' ')}] /Count ${pages.length} >>`;

  let body = '%PDF-1.4\n';
  const offsets: number[] = [];
  for (let i = 0; i < objects.length; i++) {
    offsets.push(body.length);
    body += `${i + 1} 0 obj\n${objects[i]}\nendobj\n`;
  }

  const xrefOffset = body.length;
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) {
    body += `${String(offset).padStart(10, '0')} 00000 n \n`;
  }

  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
  return new TextEncoder().encode(body);
}

export function generateDemoPdfForDoc(docId: string): Uint8Array {
  switch (docId) {
    case 'doc-app-form':
      return buildPdf([
        [
          { text: 'RETAIL LOAN APPLICATION FORM', size: 16, isBold: true },
          { text: 'Application Reference: APP-25195', size: 11, isBold: true },
          { text: 'Applicant Full Name: Ananya Sharma', size: 12 },
          { text: 'Date of Birth: 14-Aug-1994', size: 11 },
          { text: 'PAN Card ID: ABCPS4821K', size: 11 },
          { text: 'Permanent Address: 402, Green Glen Heights, Bellandur, Bangalore', size: 11 },
          { text: 'Employer: Tech Mahindra Ltd', size: 11 },
          { text: 'Employment Type: Salaried (Permanent Full-Time)', size: 11 },
          { text: 'Designation: Lead Software Engineer', size: 11 },
          { text: 'Stated Gross Monthly Salary: INR 85,000.00', size: 11, isBold: true },
          { text: 'Stated Net Monthly Salary: INR 72,500.00', size: 11, isBold: true },
          { text: 'Requested Loan Amount: INR 25,00,000.00', size: 11, isBold: true },
          { text: 'Tenure Requested: 240 Months (20 Years)', size: 11 },
        ],
        [
          { text: 'APPLICATION FORM — DECLARATION & CONSENT', size: 14, isBold: true },
          { text: 'I hereby declare that all information furnished is authentic and verifiable.', size: 10 },
          { text: 'Bank Account Number for EMI Auto-Debit: 501004899012 (HDFC Bank)', size: 11 },
          { text: 'Existing EMI Obligations: NIL', size: 11 },
          { text: 'Credit Information Bureau Authorization: GRANTED', size: 11 },
          { text: 'Applicant Signature: Signed Digitally via Aadhaar e-Sign', size: 11, isBold: true },
        ],
      ]);

    case 'doc-payslip-aug':
    case 'doc-payslip-jul':
    case 'doc-payslip-jun': {
      const monthStr =
        docId === 'doc-payslip-aug'
          ? 'August 2026'
          : docId === 'doc-payslip-jul'
          ? 'July 2026'
          : 'June 2026';
      return buildPdf([
        [
          { text: 'TECH MAHINDRA LTD — SALARY PAYSLIP', size: 15, isBold: true },
          { text: `Pay Period: ${monthStr}`, size: 11, isBold: true },
          { text: 'Employee Name: Ananya Sharma', size: 11 },
          { text: 'Employee ID: TM-789012', size: 11 },
          { text: 'Department: Enterprise Cloud Engineering', size: 11 },
          { text: 'Bank Name: HDFC Bank', size: 11 },
          { text: 'Account No: XXXXXX9012', size: 11 },
          { text: 'PAN: ABCPS4821K', size: 11 },
          { text: '-------------------------------------------------------------', size: 10 },
          { text: 'EARNINGS & ALLOWANCES', size: 12, isBold: true },
          { text: 'Basic Salary: INR 45,000.00', size: 11 },
          { text: 'House Rent Allowance (HRA): INR 22,500.00', size: 11 },
          { text: 'Special Allowance: INR 17,500.00', size: 11 },
          { text: 'Gross Earnings: 85,000.00', size: 12, isBold: true },
          { text: '-------------------------------------------------------------', size: 10 },
          { text: 'DEDUCTIONS', size: 12, isBold: true },
          { text: 'Provident Fund (PF): INR 5,400.00', size: 11 },
          { text: 'Professional Tax (PT): INR 200.00', size: 11 },
          { text: 'Income Tax (TDS): INR 6,900.00', size: 11 },
          { text: 'Total Deductions: INR 12,500.00', size: 11 },
          { text: '-------------------------------------------------------------', size: 10 },
          { text: 'Net Pay: 72,500.00', size: 13, isBold: true },
          { text: 'Payment Mode: Direct Bank Credit via NEFT/IMPS', size: 10 },
        ],
      ]);
    }

    case 'doc-bank-stmt':
      return buildPdf([
        [
          { text: 'HDFC BANK — ACCOUNT STATEMENT', size: 15, isBold: true },
          { text: 'Account Holder: Ananya Sharma', size: 11, isBold: true },
          { text: 'Account Number: 501004899012 (Masked: XXXXXX9012)', size: 11 },
          { text: 'Branch: Bellandur Outer Ring Road, Bangalore - 560103', size: 11 },
          { text: 'Statement Period: 01-Mar-2026 to 31-Aug-2026', size: 11 },
          { text: 'IFSC Code: HDFC0001234', size: 11 },
          { text: 'Monthly Average Payroll Credit: 72,500.00', size: 12, isBold: true },
          { text: 'Account Type: Resident Savings Account', size: 11 },
        ],
        [
          { text: 'HDFC BANK — PAYROLL DEPOSIT TRANSACTIONS', size: 13, isBold: true },
          { text: 'Recent Salary Credits from Tech Mahindra Ltd:', size: 11 },
          { text: '-------------------------------------------------------------', size: 10 },
          { text: '30-JUN-2026: SALARY CREDIT TECH MAHINDRA 72,500.00 (CR)', size: 11, isBold: true },
          { text: '31-JUL-2026: SALARY CREDIT TECH MAHINDRA 72,500.00 (CR)', size: 11, isBold: true },
          { text: '31-AUG-2026: SALARY CREDIT TECH MAHINDRA 72,500.00 (CR)', size: 11, isBold: true },
          { text: '-------------------------------------------------------------', size: 10 },
          { text: 'Inward Clearing Cheque Returns: 0 (Zero)', size: 11 },
          { text: 'ECS / NACH Debit Returns: 0 (Zero)', size: 11 },
        ],
        [
          { text: 'HDFC BANK — STATEMENT SUMMARY', size: 13, isBold: true },
          { text: 'Total Inward Salary Credits (6 Mos): INR 4,35,000.00', size: 11 },
          { text: 'Total Discretionary Debits: INR 2,90,000.00', size: 11 },
          { text: 'Closing Balance: 1,45,000.00', size: 13, isBold: true },
          { text: 'Total Cheque / ECS Bounces: 0', size: 12, isBold: true },
          { text: 'Account Status: ACTIVE & HEALTHY', size: 11, isBold: true },
        ],
      ]);

    case 'doc-itr-v':
      return buildPdf([
        [
          { text: 'INCOME TAX RETURN ACKNOWLEDGEMENT (ITR-V)', size: 15, isBold: true },
          { text: 'Government of India - Income Tax Department', size: 11 },
          { text: 'Assessment Year: 2024-25 (Financial Year 2023-24)', size: 11, isBold: true },
          { text: 'Form Type: ITR-1 (Sahaj)', size: 11 },
          { text: 'Assessee Name: Ananya Sharma', size: 11, isBold: true },
          { text: 'PAN: ABCPS4821K', size: 11, isBold: true },
          { text: 'Filing Date: 18-Jul-2024', size: 11 },
          { text: 'Acknowledgement Number: 849204918294819', size: 11 },
          { text: '-------------------------------------------------------------', size: 10 },
          { text: 'INCOME COMPUTATION', size: 12, isBold: true },
          { text: 'Income from Salary: INR 10,20,000.00', size: 11 },
          { text: 'Gross Total Income: 10,20,000', size: 13, isBold: true },
          { text: 'Deductions under Chapter VI-A (80C/80D): INR 1,50,000.00', size: 11 },
          { text: 'Total Taxable Income: INR 8,70,000.00', size: 11 },
          { text: 'Total Taxes Paid: 78,000', size: 12, isBold: true },
          { text: 'Refund / Balance Due: INR 0.00 (Nil)', size: 11 },
          { text: 'Verification Status: e-Verified via Aadhaar OTP on 18-Jul-2024', size: 10 },
        ],
      ]);

    case 'doc-pan-card':
      return buildPdf([
        [
          { text: 'INCOME TAX DEPARTMENT - GOVT OF INDIA', size: 14, isBold: true },
          { text: 'Permanent Account Number Card', size: 12, isBold: true },
          { text: 'Permanent Account Number: ABCPS4821K', size: 13, isBold: true },
          { text: 'Name: ANANYA SHARMA', size: 13, isBold: true },
          { text: "Father's Name: R. SHARMA", size: 11 },
          { text: 'Date of Birth: 14/08/1994', size: 11 },
          { text: 'Card Type: Individual Indian Resident', size: 11 },
          { text: 'Signature: Verified Digitally', size: 10 },
          { text: 'QR Code: Encrypted biometric authentication tag', size: 10 },
        ],
      ]);

    default:
      return buildPdf([
        [
          { text: `DOCUMENT: ${docId}`, size: 14, isBold: true },
          { text: 'Synthetic Dossier Test Document', size: 11 },
          { text: `Document Identifier: ${docId}`, size: 11 },
          { text: 'Status: Registered in dossier manifest', size: 11 },
        ],
      ]);
  }
}

/**
 * Generates an auditable, styled signed Credit Appraisal Memo (CAM) PDF receipt
 * directly in the browser for preset/offline dossiers.
 */
export function generateSignedCamPdf(application: {
  id: string;
  applicant_name: string;
  pan_masked: string;
  loan_amount?: number;
  status: string;
  reviewer_decision?: string | null;
  reviewer_notes?: string | null;
  findings: Array<{ rule_id: string; rule_name: string; verdict: string; reason: string }>;
  memo_markdown?: string;
  payslip_facts?: { net_salary?: { amount: number } | null };
  bank_facts?: { average_salary_credit?: { amount: number } | null; salary_credits?: Array<{ amount: number }> };
  tax_facts?: { gross_total_income?: { amount: number } | null };
}): Uint8Array {
  const decision = application.reviewer_decision || (application.status === 'REVIEWED' ? 'APPROVED' : 'PENDING REVIEW');
  const notes = application.reviewer_notes || 'Review executed per institutional credit underwriting guidelines.';
  const statedNet = application.payslip_facts?.net_salary?.amount
    ? `INR ${application.payslip_facts.net_salary.amount.toLocaleString()}`
    : '—';
  const avgDeposit = application.bank_facts?.average_salary_credit?.amount
    ? `INR ${application.bank_facts.average_salary_credit.amount.toLocaleString()}`
    : application.bank_facts?.salary_credits?.[0]?.amount
    ? `INR ${application.bank_facts.salary_credits[0].amount.toLocaleString()}`
    : '—';
  const taxIncome = application.tax_facts?.gross_total_income?.amount
    ? `INR ${application.tax_facts.gross_total_income.amount.toLocaleString()}`
    : '—';

  const page1Lines: PageLine[] = [
    { text: 'FINSCAN AI — CREDIT APPRAISAL MEMORANDUM', size: 15, isBold: true },
    { text: `Dossier Reference: ${application.id} | Status: ${application.status}`, size: 10, isBold: true },
    { text: '-------------------------------------------------------------------------------------------------', size: 9 },
    { text: `OFFICIAL DISPOSITION: [ ${decision} ]`, size: 13, isBold: true },
    { text: `Underwriter Reviewer Rationale: ${notes}`, size: 10 },
    { text: 'Prime Invariant: Deterministic code decides. AI explains. Human approves.', size: 9 },
    { text: '-------------------------------------------------------------------------------------------------', size: 9 },
    { text: 'APPLICANT & FINANCIAL AUDIT SUMMARY', size: 12, isBold: true },
    { text: `Applicant Full Name: ${application.applicant_name}`, size: 10 },
    { text: `Permanent Account Number (Masked): ${application.pan_masked}`, size: 10 },
    { text: `Requested Loan Amount: ${application.loan_amount ? `INR ${application.loan_amount.toLocaleString()}` : '—'}`, size: 10, isBold: true },
    { text: `Stated Net Monthly Salary: ${statedNet}`, size: 10 },
    { text: `Bank Average Monthly Credit: ${avgDeposit}`, size: 10 },
    { text: `ITR Gross Total Income: ${taxIncome}`, size: 10 },
    { text: '-------------------------------------------------------------------------------------------------', size: 9 },
    { text: 'DETERMINISTIC RULE FINDINGS', size: 12, isBold: true },
  ];

  for (const f of application.findings.slice(0, 6)) {
    const vSymbol = f.verdict.toLowerCase() === 'pass' ? '[PASS]' : f.verdict.toLowerCase() === 'flag' ? '[FLAG]' : '[UNKNOWN]';
    page1Lines.push({
      text: `${vSymbol} ${f.rule_id} (${f.rule_name}): ${f.reason}`,
      size: 9.5,
      isBold: f.verdict.toLowerCase() !== 'pass',
    });
  }

  const page2Lines: PageLine[] = [
    { text: 'CREDIT APPRAISAL MEMO (CAM) NARRATIVE', size: 14, isBold: true },
    { text: `Application ID: ${application.id}`, size: 10 },
    { text: '-------------------------------------------------------------------------------------------------', size: 9 },
  ];

  const memoLines = (application.memo_markdown || 'No memo text synthesized.').split('\n');
  for (const m of memoLines) {
    const clean = m.replace(/[*#]/g, '').trim();
    if (clean) {
      page2Lines.push({ text: clean, size: 9.5, isBold: m.startsWith('#') || m.startsWith('**') });
    }
  }

  return buildPdf([page1Lines, page2Lines]);
}
