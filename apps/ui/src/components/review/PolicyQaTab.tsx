import React, { useState } from 'react';
import { api } from '../../services/api';
import { PolicyQaResponse, PolicyCitation } from '../../types/api';
import { EvidenceRef } from '../../types/evidence';
import { sanitizePiiInText } from '../../utils/pii';
import { Send, BookOpen, ShieldCheck, ShieldAlert, Loader2, ExternalLink } from 'lucide-react';

interface PolicyQaTabProps {
  applicationId?: string;
  onSelectEvidence?: (ev: EvidenceRef) => void;
}

/**
 * A citation is navigable only when the backend gave us enough provenance to
 * actually land on a page. Policy-corpus chunks have no document_id and stay
 * read-only; document-grounded citations become jump targets.
 */
function toEvidenceRef(c: PolicyCitation): EvidenceRef | null {
  if (!c.document_id || !c.page_number) return null;
  return {
    document_id: c.document_id,
    document_type: c.document_type || 'document',
    page_number: c.page_number,
    quoted_span: c.text || '',
    bounding_box: c.bounding_box ?? null,
  };
}

const SEED_ANSWER: PolicyQaResponse = {
  question: 'What is the salary reconciliation tolerance and DTI ceiling under policy?',
  answer:
    'Under FinScan Retail Underwriting Policy v2026.1 (Section 4.2), net monthly income must be verified against at least 3 consecutive salary credits with a maximum permissible variance of ±5.0%. Debt-to-Income (DTI) ratio must not exceed 50.0% for Tier-1 applicants.',
  // Illustrative seed shown before any live retrieval — NOT a grounded answer.
  is_grounded: false,
  citations: [
    {
      chunk_id: 'POL-RET-2026-S4',
      policy_name: 'Retail Lending Credit Policy v2026.1',
      section: 'Section 4.2 — Income Verification & DTI Ceiling',
      text: 'Net salary reconciliation variance tolerance is bounded at ±5.0%. Total proposed loan EMI plus existing obligations shall not exceed 50% of verified monthly disposable income.',
      score: 0.94,
    },
  ],
};

export const PolicyQaTab: React.FC<PolicyQaTabProps> = ({ applicationId, onSelectEvidence }) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<PolicyQaResponse[]>([SEED_ANSWER]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const q = question.trim();
    if (!applicationId) {
      setHistory((prev) => [
        {
          question: q,
          answer: 'Please select an active loan dossier before querying policy guidelines.',
          is_grounded: false,
          citations: [],
        },
        ...prev,
      ]);
      return;
    }

    setLoading(true);
    setQuestion('');

    try {
      const resp = await api.askQuestion(applicationId, { question: q });
      const citations: PolicyCitation[] = (resp.citations || []).map((c) => ({
        chunk_id: c.chunk_id || '',
        policy_name: c.policy_id || c.title || 'Policy',
        section: c.section || (c.page_number ? `Page ${c.page_number}` : ''),
        text: c.excerpt || c.text || c.quoted_span || '',
        score: typeof c.score === 'number' ? c.score : 0,
        document_id: c.document_id,
        document_type: c.document_type,
        page_number: c.page_number,
        bounding_box: c.bounding_box ?? null,
      }));

      setHistory((prev) => [
        {
          question: q,
          answer: resp.answer,
          // Grounded only when the backend returned at least one citation.
          is_grounded: citations.length > 0,
          citations,
        },
        ...prev,
      ]);
    } catch (err: unknown) {
      // Surface the failure in the stream; a silent catch reads as an answer.
      setHistory((prev) => [
        {
          question: q,
          answer: `Policy Q&A request failed: ${
            err instanceof Error ? err.message : 'unknown error'
          }.`,
          is_grounded: false,
          citations: [],
        },
        ...prev,
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3.5">
      {/* Policy Search Input */}
      <form onSubmit={handleSubmit} className="relative">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask policy guidelines (e.g. DTI limits, salary tolerance)..."
          aria-label="Ask a policy question"
          className="w-full bg-theme-card border border-theme-border rounded-xs py-2 pl-3 pr-9 text-xs text-theme-primary placeholder-theme-muted focus:outline-none focus:border-theme-brand shadow-xs transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          aria-label="Submit policy question"
          className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 text-theme-muted hover:text-theme-primary disabled:opacity-40 transition-opacity cursor-pointer"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
      </form>

      {/* Q&A Stream */}
      <div className="space-y-3">
        {history.map((item, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-xs bg-theme-card border border-theme-border shadow-xs text-xs space-y-2"
          >
            <div className="flex items-start gap-2">
              <BookOpen className="w-3.5 h-3.5 text-theme-brand mt-0.5 flex-shrink-0" />
              <p className="font-serif font-bold text-theme-primary text-xs">{item.question}</p>
            </div>

            <p className="text-theme-secondary text-xs leading-relaxed pl-5.5">
              {sanitizePiiInText(item.answer)}
            </p>

            {/* Grounding banner: stated for every answer, grounded or not. */}
            <div className="mt-2 pt-2 border-t border-theme-border pl-5.5 space-y-1.5">
              <div
                className={`flex items-center gap-1.5 text-[10px] uppercase font-mono font-semibold ${
                  item.is_grounded ? 'text-theme-pass' : 'text-theme-unknown'
                }`}
              >
                {item.is_grounded ? (
                  <ShieldCheck className="w-3 h-3 flex-shrink-0" />
                ) : (
                  <ShieldAlert className="w-3 h-3 flex-shrink-0" />
                )}
                <span>
                  {item.is_grounded
                    ? `Authoritative Citation: ${item.citations[0].policy_name}`
                    : 'Unverified — illustrative example, not retrieved evidence'}
                </span>
              </div>

              {item.citations.map((c, cIdx) => {
                const ev = toEvidenceRef(c);
                const body = (
                  <>
                    {c.section && (
                      <div className="text-[10px] font-mono text-theme-muted mb-1 flex items-center justify-between gap-2">
                        <span className="truncate">{c.section}</span>
                        {c.score > 0 && (
                          <span className="tabular-nums flex-shrink-0">
                            {c.score.toFixed(2)}
                          </span>
                        )}
                      </div>
                    )}
                    <span className="italic">&ldquo;{sanitizePiiInText(c.text)}&rdquo;</span>
                  </>
                );

                // Navigable citations become jump targets into the PDF canvas.
                return ev && onSelectEvidence ? (
                  <button
                    key={cIdx}
                    type="button"
                    onClick={() => onSelectEvidence(ev)}
                    title="Click to jump and highlight on PDF canvas"
                    className="w-full text-left bg-theme-panel hover:bg-theme-card p-2 rounded-xs border border-theme-border hover:border-theme-border-card text-[11px] text-theme-secondary font-mono transition-colors cursor-pointer flex items-start justify-between gap-2"
                  >
                    <span className="min-w-0 flex-1">{body}</span>
                    <ExternalLink className="w-3 h-3 text-theme-muted flex-shrink-0 mt-0.5" />
                  </button>
                ) : (
                  <div
                    key={cIdx}
                    className="bg-theme-panel p-2 rounded-xs border border-theme-border text-[11px] text-theme-secondary font-mono"
                  >
                    {body}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
