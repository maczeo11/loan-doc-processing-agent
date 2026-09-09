/**
 * Masks Indian Permanent Account Number (PAN) to 'XXXXXX1234'.
 * Preserves strictly the last 4 characters.
 */
export function maskPan(pan?: string | null): string {
  if (!pan) return '—';
  const clean = pan.trim().toUpperCase();
  const standardMatch = clean.match(/^[A-Z]{5}(\d{4})[A-Z]$/);
  if (standardMatch) {
    return `XXXXXX${standardMatch[1]}`;
  }
  if (clean.length <= 4) return `XXXXXX${clean}`;
  return `XXXXXX${clean.slice(-4)}`;
}

/**
 * Masks Bank Account Number to 'XXXXXX1234'.
 * Preserves strictly the last 4 digits.
 */
export function maskAccountNumber(accountNumber?: string | null): string {
  if (!accountNumber) return '—';
  const clean = accountNumber.trim();
  if (clean.length <= 4) return `XXXXXX${clean}`;
  return `XXXXXX${clean.slice(-4)}`;
}

/**
 * Masks 12-digit Aadhaar to UIDAI standard 'XXXX-XXXX-1234'.
 */
export function maskAadhaar(aadhaar?: string | null): string {
  if (!aadhaar) return '—';
  const digits = aadhaar.replace(/[^0-9]/g, '');
  if (digits.length <= 4) return `XXXX-XXXX-${digits}`;
  return `XXXX-XXXX-${digits.slice(-4)}`;
}

/**
 * Scans narrative text (e.g. LLM summaries, rule reasons) and replaces
 * raw PAN, bank account, and Aadhaar numbers with masked representations.
 */
export function sanitizePiiInText(text: string): string {
  if (!text) return text;
  // Match standard PAN: 5 letters, 4 digits, 1 letter -> XXXXXX<4 digits>
  let sanitized = text.replace(/\b[A-Za-z]{5}([0-9]{4})[A-Za-z]\b/g, 'XXXXXX$1');

  // Match Aadhaar numbers (formatted or continuous 12 digits) BEFORE bank accounts
  sanitized = sanitized.replace(/\b\d{4}[ -]\d{4}[ -](\d{4})\b/g, 'XXXX-XXXX-$1');
  sanitized = sanitized.replace(/\b\d{8}(\d{4})\b/g, 'XXXX-XXXX-$1');

  // Match bank account numbers with keyword prefix (9 to 18 digits)
  sanitized = sanitized.replace(/(?:A\/C|Account|Acc|A\/c|Bank\s*A\/c)\s*[:#]?\s*(\d{9,18})\b/gi, (match, digits) => {
    return match.replace(digits, `XXXXXX${digits.slice(-4)}`);
  });

  // Match standalone bank account numbers (10 to 18 digits, preventing false positives on bare 9-digit amounts)
  sanitized = sanitized.replace(/\b\d{10,18}\b/g, (match) => {
    return `XXXXXX${match.slice(-4)}`;
  });

  return sanitized;
}

/**
 * Formats a monetary amount into Indian Rupee notation (e.g. ₹ 1,50,000.00).
 */
export function formatCurrency(amount?: number | null, currency: string = 'INR'): string {
  if (amount === undefined || amount === null || isNaN(amount)) return '—';
  const symbol = currency === 'INR' ? '₹' : currency;
  try {
    const formatted = new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
    return `${symbol} ${formatted}`;
  } catch {
    return `${symbol} ${amount.toFixed(2)}`;
  }
}
