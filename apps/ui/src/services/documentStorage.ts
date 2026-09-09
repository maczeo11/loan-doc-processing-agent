import { ApiService } from './api';

interface CachedUrl {
  url: string;
  expiresAt: number;
}

export class DocumentStorageService {
  private static cache: Map<string, CachedUrl> = new Map();

  /**
   * Retrieves a signed URL for a given document with 60s pre-expiration buffer.
   */
  static async getSignedUrl(appId: string, docId: string): Promise<string> {
    const key = `${appId}:${docId}`;
    const cached = this.cache.get(key);
    const now = Date.now();

    // Cache hit if more than 60 seconds remaining
    if (cached && cached.expiresAt - now > 60 * 1000) {
      return cached.url;
    }

    try {
      const freshUrl = await ApiService.getDocumentSignedUrl(appId, docId);
      // Default 15 minute TTL
      this.cache.set(key, {
        url: freshUrl,
        expiresAt: now + 15 * 60 * 1000,
      });
      return freshUrl;
    } catch {
      // Fallback
      const fallbackUrl = `/files/dossiers/${appId}/${docId}.pdf`;
      this.cache.set(key, {
        url: fallbackUrl,
        expiresAt: now + 5 * 60 * 1000,
      });
      return fallbackUrl;
    }
  }

  /**
   * Invalidates cached URL if 403 Forbidden or expired.
   */
  static invalidate(appId: string, docId: string): void {
    const key = `${appId}:${docId}`;
    this.cache.delete(key);
  }

  /**
   * Generates a minimal valid synthetic PDF blob URL with watermark
   * for testing canvas rendering when backend files are offline.
   */
  static createDemoPdfBlob(title: string, contentLines: string[]): string {
    const escapedTitle = title.replace(/[()\\]/g, '');
    const lines = contentLines.map((l, i) => `1 0 0 1 50 ${680 - i * 22} Tm (${l.replace(/[()\\]/g, '')}) Tj`).join('\n');

    const pdfContent = `%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length 500 >> stream
BT
/F1 16 Tf
1 0 0 1 50 780 Tm
(${escapedTitle}) Tj
/F1 12 Tf
0.6 0.2 0.2 rg
1 0 0 1 50 750 Tm
(*** SYNTHETIC DEMO -- NOT VALID FOR BANKING ***) Tj
0 0 0 rg
/F1 11 Tf
${lines}
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000117 00000 n 
0000000226 00000 n 
0000000300 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
860
%%EOF`;

    const blob = new Blob([pdfContent], { type: 'application/pdf' });
    return URL.createObjectURL(blob);
  }
}
