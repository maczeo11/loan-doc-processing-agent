import type { LoanApplicationState } from '../types/contracts';

/**
 * Isolated demo dossier representing APP-25195 in READY_FOR_REVIEW state.
 * Archetype: Clean Baseline (All Passes).
 */
export const DEMO_DOSSIER_APP_25195: LoanApplicationState = {
  application_id: 'APP-25195',
  status: 'READY_FOR_REVIEW',
  status_history: [
    { from_status: 'UPLOADED', to_status: 'QUEUED', timestamp: '2026-09-08T10:00:00Z', reason: 'User submitted for processing' },
    { from_status: 'QUEUED', to_status: 'PROCESSING', timestamp: '2026-09-08T10:00:02Z', reason: 'Worker picked up job' },
    { from_status: 'PROCESSING', to_status: 'READY_FOR_REVIEW', timestamp: '2026-09-08T10:00:45Z', reason: 'Pipeline halted at human review checkpoint' },
  ],
  document_ids: [
    'doc-app-form',
    'doc-payslip-jun',
    'doc-payslip-jul',
    'doc-payslip-aug',
    'doc-bank-stmt',
    'doc-itr-v',
    'doc-pan-card',
  ],
  document_manifest: {
    'doc-app-form': 'dossiers/APP-25195/doc-app-form_application.pdf',
    'doc-payslip-jun': 'dossiers/APP-25195/doc-payslip-jun_payslip_june.pdf',
    'doc-payslip-jul': 'dossiers/APP-25195/doc-payslip-jul_payslip_july.pdf',
    'doc-payslip-aug': 'dossiers/APP-25195/doc-payslip-aug_payslip_august.pdf',
    'doc-bank-stmt': 'dossiers/APP-25195/doc-bank-stmt_bank_statement.pdf',
    'doc-itr-v': 'dossiers/APP-25195/doc-itr-v_itr_acknowledgement.pdf',
    'doc-pan-card': 'dossiers/APP-25195/doc-pan-card_pan_card.pdf',
  },
  classified_types: {
    'doc-app-form': 'application_form',
    'doc-payslip-jun': 'payslip',
    'doc-payslip-jul': 'payslip',
    'doc-payslip-aug': 'payslip',
    'doc-bank-stmt': 'bank_statement',
    'doc-itr-v': 'tax_return',
    'doc-pan-card': 'id_card',
  },
  applicant: {
    full_name: 'Ananya Sharma',
    pan_number: 'XXXXXX4821',
    source_name: {
      document_id: 'doc-pan-card',
      document_type: 'id_card',
      page_number: 1,
      quoted_span: 'ANANYA SHARMA',
      bounding_box: { x0: 0.295, y0: 0.157, x1: 0.53, y1: 0.173 },
    },
    source_pan: {
      document_id: 'doc-pan-card',
      document_type: 'id_card',
      page_number: 1,
      quoted_span: 'ABCPS4821K',
      bounding_box: { x0: 0.295, y0: 0.133, x1: 0.721, y1: 0.149 },
    },
  },
  payslip: {
    employee_name: 'Ananya Sharma',
    employer_name: 'Tech Mahindra Ltd',
    gross_salary: {
      amount: 85000,
      currency: 'INR',
      period: 'monthly',
      basis: 'gross',
      source: {
        document_id: 'doc-payslip-aug',
        document_type: 'payslip',
        page_number: 1,
        quoted_span: 'Gross Earnings: 85,000.00',
        bounding_box: { x0: 0.295, y0: 0.371, x1: 0.565, y1: 0.386 },
      },
    },
    net_salary: {
      amount: 72500,
      currency: 'INR',
      period: 'monthly',
      basis: 'net',
      source: {
        document_id: 'doc-payslip-aug',
        document_type: 'payslip',
        page_number: 1,
        quoted_span: 'Net Pay: 72,500.00',
        bounding_box: { x0: 0.295, y0: 0.56, x1: 0.52, y1: 0.576 },
      },
    },
    pay_period_str: 'August 2026',
  },
  bank_statement: {
    account_holder: 'Ananya Sharma',
    bank_name: 'HDFC Bank',
    account_number_masked: 'XXXXXX9012',
    salary_credits: [
      {
        amount: 72500,
        currency: 'INR',
        period: 'monthly',
        basis: 'net',
        source: {
          document_id: 'doc-bank-stmt',
          document_type: 'bank_statement',
          page_number: 2,
          quoted_span: 'SALARY CREDIT TECH MAHINDRA 72,500.00',
          bounding_box: { x0: 0.295, y0: 0.206, x1: 0.842, y1: 0.22 },
        },
      },
    ],
    average_salary_credit: {
      amount: 72500,
      currency: 'INR',
      period: 'monthly',
      basis: 'net',
      source: {
        document_id: 'doc-bank-stmt',
        document_type: 'bank_statement',
        page_number: 1,
        quoted_span: 'Monthly Average Payroll Credit: 72,500.00',
        bounding_box: { x0: 0.295, y0: 0.229, x1: 0.733, y1: 0.244 },
      },
    },
    closing_balance: {
      amount: 145000,
      currency: 'INR',
      period: 'one_time',
      basis: 'balance',
      source: {
        document_id: 'doc-bank-stmt',
        document_type: 'bank_statement',
        page_number: 3,
        quoted_span: 'Closing Balance: 1,45,000.00',
        bounding_box: { x0: 0.295, y0: 0.157, x1: 0.631, y1: 0.173 },
      },
    },
    bounced_transactions: 0,
  },
  tax_return: {
    assessee_name: 'Ananya Sharma',
    pan_number: 'XXXXXX4821',
    assessment_year: '2024-25',
    gross_total_income: {
      amount: 1020000,
      currency: 'INR',
      period: 'annual',
      basis: 'gross',
      source: {
        document_id: 'doc-itr-v',
        document_type: 'tax_return',
        page_number: 1,
        quoted_span: 'Gross Total Income: 10,20,000',
        bounding_box: { x0: 0.295, y0: 0.347, x1: 0.631, y1: 0.363 },
      },
    },
    total_tax_paid: {
      amount: 78000,
      currency: 'INR',
      period: 'annual',
      basis: 'deduction',
      source: {
        document_id: 'doc-itr-v',
        document_type: 'tax_return',
        page_number: 1,
        quoted_span: 'Total Taxes Paid: 78,000',
        bounding_box: { x0: 0.295, y0: 0.419, x1: 0.565, y1: 0.434 },
      },
    },
  },
  findings: [
    {
      rule_id: 'RULE-COMP-01',
      rule_name: 'Dossier Completeness Audit',
      verdict: 'pass',
      reason: 'All 5 mandatory document categories (Application Form, 3x Payslips, Bank Statement, ITR-V, ID Proof) are present and verified.',
      supporting_evidence: [
        {
          document_id: 'doc-app-form',
          document_type: 'application_form',
          page_number: 1,
          quoted_span: 'Loan Application Form - Verified',
          bounding_box: { x0: 0.295, y0: 0.082, x1: 0.733, y1: 0.101 },
          confidence: 0.95,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-INC-01',
      rule_name: 'Salary to Payroll Deposit Reconciliation',
      verdict: 'pass',
      reason: 'Stated payslip net salary (INR 72,500) perfectly matches average monthly bank payroll credit (INR 72,500) within 5.0% tolerance.',
      supporting_evidence: [
        {
          document_id: 'doc-payslip-aug',
          document_type: 'payslip',
          page_number: 1,
          quoted_span: 'Net Pay: 72,500.00',
          bounding_box: { x0: 0.295, y0: 0.56, x1: 0.52, y1: 0.576 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
        {
          document_id: 'doc-bank-stmt',
          document_type: 'bank_statement',
          page_number: 2,
          quoted_span: '31-AUG-2026: SALARY CREDIT TECH MAHINDRA 72,500.00 (CR)',
          bounding_box: { x0: 0.295, y0: 0.206, x1: 0.842, y1: 0.22 },
          confidence: 0.98,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-TAX-01',
      rule_name: 'ITR Gross Income vs Annualized Salary Audit',
      verdict: 'pass',
      reason: 'Annualized payslip gross (12 x INR 85,000 = INR 10,20,000) aligns exactly with ITR-V Gross Total Income (INR 10,20,000).',
      supporting_evidence: [
        {
          document_id: 'doc-itr-v',
          document_type: 'tax_return',
          page_number: 1,
          quoted_span: 'Gross Total Income: 10,20,000',
          bounding_box: { x0: 0.295, y0: 0.347, x1: 0.631, y1: 0.363 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-ID-01',
      rule_name: 'Applicant Identity & PAN Reconciliation',
      verdict: 'pass',
      reason: 'Applicant name "Ananya Sharma" and masked PAN "XXXXXX4821" match across PAN Card, ITR-V, Bank Statement, and Payslips.',
      supporting_evidence: [
        {
          document_id: 'doc-pan-card',
          document_type: 'id_card',
          page_number: 1,
          quoted_span: 'Permanent Account Number: ABCPS4821K',
          bounding_box: { x0: 0.295, y0: 0.133, x1: 0.721, y1: 0.149 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
  ],
  missing_documents: [],
  summary_markdown: `### Credit Appraisal Summary (CAM)\n**Applicant:** Ananya Sharma | **Application ID:** APP-25195\n- **Income Verification:** Stated net monthly salary of INR 72,500 is corroborated by consistent bank credits at Tech Mahindra Ltd.\n- **Tax Filing:** ITR-V for AY 2024-25 confirms annualized gross income of INR 10,20,000 with zero bounced transactions.\n- **Recommendation:** Pipeline halted at human underwriter sign-off checkpoint for final authorization.`,
  summary_grounded: true,
  review_paused: true,
};

/**
 * Isolated demo dossier representing APP-68210 in READY_FOR_REVIEW state.
 * Archetype: Salary Mismatch (Flag on RULE-INC-01).
 */
export const DEMO_DOSSIER_APP_68210: LoanApplicationState = {
  application_id: 'APP-68210',
  status: 'READY_FOR_REVIEW',
  status_history: [
    { from_status: 'UPLOADED', to_status: 'QUEUED', timestamp: '2026-09-08T11:15:00Z', reason: 'User submitted for processing' },
    { from_status: 'QUEUED', to_status: 'PROCESSING', timestamp: '2026-09-08T11:15:03Z', reason: 'Worker picked up job' },
    { from_status: 'PROCESSING', to_status: 'READY_FOR_REVIEW', timestamp: '2026-09-08T11:15:42Z', reason: 'Discrepancy detected in payroll reconciliation' },
  ],
  document_ids: [
    'doc-app-form',
    'doc-payslip-jun',
    'doc-payslip-jul',
    'doc-payslip-aug',
    'doc-bank-stmt',
    'doc-itr-v',
    'doc-pan-card',
  ],
  document_manifest: {
    'doc-app-form': 'dossiers/APP-68210/doc-app-form_application.pdf',
    'doc-payslip-jun': 'dossiers/APP-68210/doc-payslip-jun_payslip_june.pdf',
    'doc-payslip-jul': 'dossiers/APP-68210/doc-payslip-jul_payslip_july.pdf',
    'doc-payslip-aug': 'dossiers/APP-68210/doc-payslip-aug_payslip_august.pdf',
    'doc-bank-stmt': 'dossiers/APP-68210/doc-bank-stmt_bank_statement.pdf',
    'doc-itr-v': 'dossiers/APP-68210/doc-itr-v_itr_acknowledgement.pdf',
    'doc-pan-card': 'dossiers/APP-68210/doc-pan-card_pan_card.pdf',
  },
  classified_types: {
    'doc-app-form': 'application_form',
    'doc-payslip-jun': 'payslip',
    'doc-payslip-jul': 'payslip',
    'doc-payslip-aug': 'payslip',
    'doc-bank-stmt': 'bank_statement',
    'doc-itr-v': 'tax_return',
    'doc-pan-card': 'id_card',
  },
  applicant: {
    full_name: 'Rajesh Verma',
    pan_number: 'XXXXXX5192',
    source_name: {
      document_id: 'doc-pan-card',
      document_type: 'id_card',
      page_number: 1,
      quoted_span: 'RAJESH VERMA',
      bounding_box: { x0: 0.295, y0: 0.157, x1: 0.53, y1: 0.173 },
    },
    source_pan: {
      document_id: 'doc-pan-card',
      document_type: 'id_card',
      page_number: 1,
      quoted_span: 'BKPVR5192M',
      bounding_box: { x0: 0.295, y0: 0.133, x1: 0.721, y1: 0.149 },
    },
  },
  payslip: {
    employee_name: 'Rajesh Verma',
    employer_name: 'Apex Infotech Solutions',
    gross_salary: {
      amount: 105000,
      currency: 'INR',
      period: 'monthly',
      basis: 'gross',
      source: {
        document_id: 'doc-payslip-aug',
        document_type: 'payslip',
        page_number: 1,
        quoted_span: 'Gross Earnings: 1,05,000.00',
        bounding_box: { x0: 0.295, y0: 0.371, x1: 0.565, y1: 0.386 },
      },
    },
    net_salary: {
      amount: 85000,
      currency: 'INR',
      period: 'monthly',
      basis: 'net',
      source: {
        document_id: 'doc-payslip-aug',
        document_type: 'payslip',
        page_number: 1,
        quoted_span: 'Net Pay: 85,000.00',
        bounding_box: { x0: 0.295, y0: 0.56, x1: 0.52, y1: 0.576 },
      },
    },
    pay_period_str: 'August 2026',
  },
  bank_statement: {
    account_holder: 'Rajesh Verma',
    bank_name: 'Axis Bank',
    account_number_masked: 'XXXXXX3481',
    salary_credits: [
      {
        amount: 62000,
        currency: 'INR',
        period: 'monthly',
        basis: 'net',
        source: {
          document_id: 'doc-bank-stmt',
          document_type: 'bank_statement',
          page_number: 2,
          quoted_span: '31-AUG-2026: SALARY CREDIT APEX INFO 62,000.00',
          bounding_box: { x0: 0.295, y0: 0.206, x1: 0.842, y1: 0.22 },
        },
      },
    ],
    average_salary_credit: {
      amount: 62000,
      currency: 'INR',
      period: 'monthly',
      basis: 'net',
      source: {
        document_id: 'doc-bank-stmt',
        document_type: 'bank_statement',
        page_number: 1,
        quoted_span: 'Average Salary Deposit: 62,000.00',
        bounding_box: { x0: 0.295, y0: 0.229, x1: 0.733, y1: 0.244 },
      },
    },
    closing_balance: {
      amount: 82000,
      currency: 'INR',
      period: 'one_time',
      basis: 'balance',
      source: {
        document_id: 'doc-bank-stmt',
        document_type: 'bank_statement',
        page_number: 3,
        quoted_span: 'Closing Balance: 82,000.00',
        bounding_box: { x0: 0.295, y0: 0.157, x1: 0.631, y1: 0.173 },
      },
    },
    bounced_transactions: 1,
  },
  tax_return: {
    assessee_name: 'Rajesh Verma',
    pan_number: 'XXXXXX5192',
    assessment_year: '2024-25',
    gross_total_income: {
      amount: 840000,
      currency: 'INR',
      period: 'annual',
      basis: 'gross',
      source: {
        document_id: 'doc-itr-v',
        document_type: 'tax_return',
        page_number: 1,
        quoted_span: 'Gross Total Income: 8,40,000',
        bounding_box: { x0: 0.295, y0: 0.347, x1: 0.631, y1: 0.363 },
      },
    },
    total_tax_paid: {
      amount: 54000,
      currency: 'INR',
      period: 'annual',
      basis: 'deduction',
      source: {
        document_id: 'doc-itr-v',
        document_type: 'tax_return',
        page_number: 1,
        quoted_span: 'Total Taxes Paid: 54,000',
        bounding_box: { x0: 0.295, y0: 0.419, x1: 0.565, y1: 0.434 },
      },
    },
  },
  findings: [
    {
      rule_id: 'RULE-COMP-01',
      rule_name: 'Dossier Completeness Audit',
      verdict: 'pass',
      reason: 'All mandatory loan application documents are present and validated.',
      supporting_evidence: [
        {
          document_id: 'doc-app-form',
          document_type: 'application_form',
          page_number: 1,
          quoted_span: 'Retail Loan Application Form (Verified)',
          bounding_box: { x0: 0.295, y0: 0.082, x1: 0.733, y1: 0.101 },
          confidence: 0.96,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-INC-01',
      rule_name: 'Salary to Payroll Deposit Reconciliation',
      verdict: 'flag',
      reason: 'PAYROLL MISMATCH DETECTED: Stated net salary on payslip is INR 85,000, but average actual bank deposit is INR 62,000 (-27.1% discrepancy). Exceeds 5.0% threshold.',
      supporting_evidence: [
        {
          document_id: 'doc-payslip-aug',
          document_type: 'payslip',
          page_number: 1,
          quoted_span: 'Net Pay: 85,000.00',
          bounding_box: { x0: 0.295, y0: 0.56, x1: 0.52, y1: 0.576 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
        {
          document_id: 'doc-bank-stmt',
          document_type: 'bank_statement',
          page_number: 2,
          quoted_span: '31-AUG-2026: SALARY CREDIT APEX INFO 62,000.00',
          bounding_box: { x0: 0.295, y0: 0.206, x1: 0.842, y1: 0.22 },
          confidence: 0.98,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-TAX-01',
      rule_name: 'ITR Gross Income vs Annualized Salary Audit',
      verdict: 'flag',
      reason: 'TAX UNDERREPORTING: Annualized payslip gross (INR 12,60,000) exceeds reported ITR gross income (INR 8,40,000) by INR 4,20,000 (+33.3%).',
      supporting_evidence: [
        {
          document_id: 'doc-itr-v',
          document_type: 'tax_return',
          page_number: 1,
          quoted_span: 'Gross Total Income: 8,40,000',
          bounding_box: { x0: 0.295, y0: 0.347, x1: 0.631, y1: 0.363 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-ID-01',
      rule_name: 'Applicant Identity & PAN Reconciliation',
      verdict: 'pass',
      reason: 'Identity credentials match across PAN Card and Application Form.',
      supporting_evidence: [
        {
          document_id: 'doc-pan-card',
          document_type: 'id_card',
          page_number: 1,
          quoted_span: 'Permanent Account Number: BKPVR5192M',
          bounding_box: { x0: 0.295, y0: 0.133, x1: 0.721, y1: 0.149 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
  ],
  missing_documents: [],
  summary_markdown: `### Credit Appraisal Summary (CAM)\n**Applicant:** Rajesh Verma | **Application ID:** APP-68210\n- **HIGH RISK FLAG — Income Discrepancy:** The applicant stated a monthly net income of INR 85,000 on payslips, but verified bank credits reflect only INR 62,000 (-27.1% delta).\n- **Tax Filing:** ITR-V declares INR 8,40,000 vs annualized gross of INR 12,60,000.\n- **Recommendation:** Mandatory REJECTION or formal Request for Information (NEEDS_INFO) regarding secondary payroll deductions.`,
  summary_grounded: true,
  review_paused: true,
};

/**
 * Isolated demo dossier representing APP-10492 in READY_FOR_REVIEW state.
 * Archetype: Identity Discrepancy (Flag on RULE-ID-01).
 */
export const DEMO_DOSSIER_APP_10492: LoanApplicationState = {
  application_id: 'APP-10492',
  status: 'READY_FOR_REVIEW',
  status_history: [
    { from_status: 'UPLOADED', to_status: 'QUEUED', timestamp: '2026-09-08T12:00:00Z', reason: 'User submitted for processing' },
    { from_status: 'QUEUED', to_status: 'PROCESSING', timestamp: '2026-09-08T12:00:02Z', reason: 'Worker picked up job' },
    { from_status: 'PROCESSING', to_status: 'READY_FOR_REVIEW', timestamp: '2026-09-08T12:00:39Z', reason: 'Identity verification discrepancy flagged' },
  ],
  document_ids: [
    'doc-app-form',
    'doc-payslip-jun',
    'doc-payslip-jul',
    'doc-payslip-aug',
    'doc-bank-stmt',
    'doc-itr-v',
    'doc-pan-card',
  ],
  document_manifest: {
    'doc-app-form': 'dossiers/APP-10492/doc-app-form_application.pdf',
    'doc-payslip-jun': 'dossiers/APP-10492/doc-payslip-jun_payslip_june.pdf',
    'doc-payslip-jul': 'dossiers/APP-10492/doc-payslip-jul_payslip_july.pdf',
    'doc-payslip-aug': 'dossiers/APP-10492/doc-payslip-aug_payslip_august.pdf',
    'doc-bank-stmt': 'dossiers/APP-10492/doc-bank-stmt_bank_statement.pdf',
    'doc-itr-v': 'dossiers/APP-10492/doc-itr-v_itr_acknowledgement.pdf',
    'doc-pan-card': 'dossiers/APP-10492/doc-pan-card_pan_card.pdf',
  },
  classified_types: {
    'doc-app-form': 'application_form',
    'doc-payslip-jun': 'payslip',
    'doc-payslip-jul': 'payslip',
    'doc-payslip-aug': 'payslip',
    'doc-bank-stmt': 'bank_statement',
    'doc-itr-v': 'tax_return',
    'doc-pan-card': 'id_card',
  },
  applicant: {
    full_name: 'Pooja Iyer',
    pan_number: 'XXXXXX8812',
    source_name: {
      document_id: 'doc-pan-card',
      document_type: 'id_card',
      page_number: 1,
      quoted_span: 'PUJA IYER',
      bounding_box: { x0: 0.295, y0: 0.157, x1: 0.53, y1: 0.173 },
    },
    source_pan: {
      document_id: 'doc-pan-card',
      document_type: 'id_card',
      page_number: 1,
      quoted_span: 'ABCPI8812K',
      bounding_box: { x0: 0.295, y0: 0.133, x1: 0.721, y1: 0.149 },
    },
  },
  payslip: {
    employee_name: 'Pooja Iyer',
    employer_name: 'Wipro Technologies',
    gross_salary: {
      amount: 95000,
      currency: 'INR',
      period: 'monthly',
      basis: 'gross',
      source: {
        document_id: 'doc-payslip-aug',
        document_type: 'payslip',
        page_number: 1,
        quoted_span: 'Gross Earnings: 95,000.00',
        bounding_box: { x0: 0.295, y0: 0.371, x1: 0.565, y1: 0.386 },
      },
    },
    net_salary: {
      amount: 79000,
      currency: 'INR',
      period: 'monthly',
      basis: 'net',
      source: {
        document_id: 'doc-payslip-aug',
        document_type: 'payslip',
        page_number: 1,
        quoted_span: 'Net Pay: 79,000.00',
        bounding_box: { x0: 0.295, y0: 0.56, x1: 0.52, y1: 0.576 },
      },
    },
    pay_period_str: 'August 2026',
  },
  bank_statement: {
    account_holder: 'Pooja Iyer',
    bank_name: 'State Bank of India',
    account_number_masked: 'XXXXXX2940',
    salary_credits: [
      {
        amount: 79000,
        currency: 'INR',
        period: 'monthly',
        basis: 'net',
        source: {
          document_id: 'doc-bank-stmt',
          document_type: 'bank_statement',
          page_number: 2,
          quoted_span: '31-AUG-2026: SALARY CREDIT WIPRO 79,000.00',
          bounding_box: { x0: 0.295, y0: 0.206, x1: 0.842, y1: 0.22 },
        },
      },
    ],
    average_salary_credit: {
      amount: 79000,
      currency: 'INR',
      period: 'monthly',
      basis: 'net',
      source: {
        document_id: 'doc-bank-stmt',
        document_type: 'bank_statement',
        page_number: 1,
        quoted_span: 'Average Salary Deposit: 79,000.00',
        bounding_box: { x0: 0.295, y0: 0.229, x1: 0.733, y1: 0.244 },
      },
    },
    closing_balance: {
      amount: 190000,
      currency: 'INR',
      period: 'one_time',
      basis: 'balance',
      source: {
        document_id: 'doc-bank-stmt',
        document_type: 'bank_statement',
        page_number: 3,
        quoted_span: 'Closing Balance: 1,90,000.00',
        bounding_box: { x0: 0.295, y0: 0.157, x1: 0.631, y1: 0.173 },
      },
    },
    bounced_transactions: 0,
  },
  tax_return: {
    assessee_name: 'Puja Iyer',
    pan_number: 'XXXXXX8812',
    assessment_year: '2024-25',
    gross_total_income: {
      amount: 1140000,
      currency: 'INR',
      period: 'annual',
      basis: 'gross',
      source: {
        document_id: 'doc-itr-v',
        document_type: 'tax_return',
        page_number: 1,
        quoted_span: 'Gross Total Income: 11,40,000',
        bounding_box: { x0: 0.295, y0: 0.347, x1: 0.631, y1: 0.363 },
      },
    },
    total_tax_paid: {
      amount: 88000,
      currency: 'INR',
      period: 'annual',
      basis: 'deduction',
      source: {
        document_id: 'doc-itr-v',
        document_type: 'tax_return',
        page_number: 1,
        quoted_span: 'Total Taxes Paid: 88,000',
        bounding_box: { x0: 0.295, y0: 0.419, x1: 0.565, y1: 0.434 },
      },
    },
  },
  findings: [
    {
      rule_id: 'RULE-COMP-01',
      rule_name: 'Dossier Completeness Audit',
      verdict: 'pass',
      reason: 'All 5 mandatory document categories are present and readable.',
      supporting_evidence: [
        {
          document_id: 'doc-app-form',
          document_type: 'application_form',
          page_number: 1,
          quoted_span: 'Loan Application Form - Verified',
          bounding_box: { x0: 0.295, y0: 0.082, x1: 0.733, y1: 0.101 },
          confidence: 0.95,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-INC-01',
      rule_name: 'Salary to Payroll Deposit Reconciliation',
      verdict: 'pass',
      reason: 'Stated payslip net salary (INR 79,000) matches average bank payroll credit (INR 79,000) within tolerance.',
      supporting_evidence: [
        {
          document_id: 'doc-payslip-aug',
          document_type: 'payslip',
          page_number: 1,
          quoted_span: 'Net Pay: 79,000.00',
          bounding_box: { x0: 0.295, y0: 0.56, x1: 0.52, y1: 0.576 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-TAX-01',
      rule_name: 'ITR Gross Income vs Annualized Salary Audit',
      verdict: 'pass',
      reason: 'Annualized payslip gross (12 x INR 95,000 = INR 11,40,000) aligns with ITR-V Gross Total Income.',
      supporting_evidence: [
        {
          document_id: 'doc-itr-v',
          document_type: 'tax_return',
          page_number: 1,
          quoted_span: 'Gross Total Income: 11,40,000',
          bounding_box: { x0: 0.295, y0: 0.347, x1: 0.631, y1: 0.363 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
      ],
      policy_version: 'v1.0',
    },
    {
      rule_id: 'RULE-ID-01',
      rule_name: 'Applicant Identity & PAN Reconciliation',
      verdict: 'flag',
      reason: 'KYC NAME DISCREPANCY: Application and payslips state "Pooja Iyer", but government PAN card states "PUJA IYER" (Fuzzy similarity 0.82 < 0.90 threshold).',
      supporting_evidence: [
        {
          document_id: 'doc-pan-card',
          document_type: 'id_card',
          page_number: 1,
          quoted_span: 'Name: PUJA IYER | PAN: ABCPI8812K',
          bounding_box: { x0: 0.295, y0: 0.157, x1: 0.53, y1: 0.173 },
          confidence: 0.97,
          extraction_method: 'paddle_ocr',
        },
      ],
      policy_version: 'v1.0',
    },
  ],
  missing_documents: [],
  summary_markdown: `### Credit Appraisal Summary (CAM)\n**Applicant:** Pooja Iyer | **Application ID:** APP-10492\n- **Income & Taxes:** Fully verified and compliant. Monthly net INR 79,000.\n- **KYC Discrepancy:** First name spelling discrepancy detected between government PAN record ("PUJA") and loan dossier ("POOJA").\n- **Recommendation:** Request notarized name affidavit or Aadhaar verification before committee approval.`,
  summary_grounded: true,
  review_paused: true,
};

export const DEMO_DOSSIERS: Record<string, LoanApplicationState> = {
  'APP-25195': DEMO_DOSSIER_APP_25195,
  'APP-68210': DEMO_DOSSIER_APP_68210,
  'APP-10492': DEMO_DOSSIER_APP_10492,
};

export const DEMO_DOSSIER_IDS = Object.keys(DEMO_DOSSIERS);

export function isDemoDossierId(appId: string): boolean {
  return Object.prototype.hasOwnProperty.call(DEMO_DOSSIERS, appId);
}

/**
 * Returns the preset for a demo archetype, or `null` for anything else.
 *
 * This deliberately does NOT fall back to a default dossier: returning
 * APP-25195 for an unknown id meant a backend outage silently showed one
 * applicant's facts, findings and READY_FOR_REVIEW status under a different
 * applicant's application id — with sign-off enabled.
 */
export function getDemoDossier(appId: string): LoanApplicationState | null {
  return DEMO_DOSSIERS[appId] ?? null;
}
