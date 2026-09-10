import React, { useState } from 'react';
import { api } from '../../services/api';
import { PolicyQaResponse } from '../../types/api';
import { EvidenceRef } from '../../types/evidence';
import { Send, BookOpen, ShieldCheck, Loader2 } from 'lucide-react';

interface PolicyQaTabProps {
  applicationId?: string;
  onSelectEvidence?: (ev: EvidenceRef) => void;
}

export const PolicyQaTab: React.FC<PolicyQaTabProps> = ({ applicationId }) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<PolicyQaResponse[]>([
    {
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
    },
  ]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const q = question.trim();
    setLoading(true);
    setError(null);
    setQuestion('');

    try {
      const resp = await api.askQuestion(applicationId || 'APP-25195', { question: q });
      setHistory((prev) => [{
        question: q,
        answer: resp.answer,
        // Grounded only when the backend returns at least one citation.
        is_grounded: (resp.citations || []).length > 0,
        citations: (resp.citations || []).map((c: {
          chunk_id?: string; doc_id?: string; title?: string; section?: string;
          excerpt?: string; text?: string; score?: number; page_number?: number;
        }) => ({
          chunk_id: c.chunk_id || '',
          policy_name: c.doc_id || c.title || 'Policy',
          section: c.section || (c.page_number ? `Page ${c.page_number}` : ''),
          text: c.excerpt || c.text || '',
          score: typeof c.score === 'number' ? c.score : 0,
        })),
      }, ...prev]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Policy Q&A request failed.');
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
          className="w-full bg-white border border-[#E3DDD3] rounded py-2 pl-3 pr-9 text-xs text-stone-900 placeholder-stone-400 focus:outline-none focus:border-stone-800 shadow-xs transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 text-stone-600 hover:text-stone-900 disabled:opacity-40 transition-opacity"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
      </form>

      {/* Q&A Stream */}
      <div className="space-y-3">
        {error && (
          <div className="p-2.5 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            Policy Q&A error: {error}
          </div>
        )}
        {history.map((item, idx) => (
          <div key={idx} className="p-3.5 rounded bg-white border border-[#E3DDD3] shadow-sm text-xs space-y-2">
            <div className="flex items-start gap-2">
              <BookOpen className="w-3.5 h-3.5 text-[#14532D] mt-0.5 flex-shrink-0" />
              <p className="font-serif font-bold text-stone-900 text-xs">{item.question}</p>
            </div>

            <p className="text-stone-700 text-xs leading-relaxed pl-5.5">
              {item.answer}
            </p>

            {item.citations.length > 0 && (
              <div className="mt-2 pt-2 border-t border-[#E3DDD3] pl-5.5 space-y-1.5">
                <div className="flex items-center gap-1.5 text-[10px] uppercase font-mono font-semibold text-[#14532D]">
                  <ShieldCheck className="w-3 h-3" />
                  <span>
                    {item.is_grounded
                      ? `Authoritative Citation: ${item.citations[0].policy_name}`
                      : 'Unverified — illustrative example, not retrieved evidence'}
                  </span>
                </div>
                <div className="p-2 rounded bg-[#FBF9F5] border border-[#E3DDD3] text-[11px] font-mono text-stone-800">
                  <p className="text-stone-500 mb-1 text-[10px] font-bold">
                    {item.citations[0].section} (Score: {(item.citations[0].score * 100).toFixed(0)}%)
                  </p>
                  <p className="italic font-serif">&ldquo;{item.citations[0].text}&rdquo;</p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
