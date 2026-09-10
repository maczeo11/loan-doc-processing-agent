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
  // No seeded answers: an empty policy Q&A shows an empty state, never
  // a fabricated grounded response.
  const [history, setHistory] = useState<PolicyQaResponse[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const q = question.trim();
    setLoading(true);
    setQuestion('');

    try {
      const resp = await api.askQuestion(applicationId || 'APP-25195', { question: q });
      setHistory((prev) => [
        {
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
        },
        ...prev,
      ]);
    } catch (err: unknown) {
      setHistory((prev) => [
        {
          question: q,
          answer: `Policy Q&A request failed: ${err instanceof Error ? err.message : 'unknown error'}.`,
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
          className="w-full bg-theme-card border border-theme-border rounded-xs py-2 pl-3 pr-9 text-xs text-theme-primary placeholder-theme-muted focus:outline-none focus:border-theme-brand shadow-xs transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 text-theme-muted hover:text-theme-primary disabled:opacity-40 transition-opacity cursor-pointer"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
      </form>

      {/* Q&A Stream */}
      <div className="space-y-3">
        {history.length === 0 && !loading && (
          <div className="p-4 rounded-xs bg-theme-panel border border-theme-border text-center space-y-1.5">
            <p className="text-xs font-bold text-theme-primary font-mono">No policy questions yet</p>
            <p className="text-[11px] text-theme-secondary">
              Ask about DTI limits, salary tolerance, or KYC rules — answers cite
              retrieved policy passages only.
            </p>
          </div>
        )}
        {history.map((item, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-xs bg-theme-card border border-theme-border shadow-xs text-xs space-y-2"
          >
            <div className="flex items-start gap-2">
              <BookOpen className="w-3.5 h-3.5 text-theme-pass mt-0.5 flex-shrink-0" />
              <p className="font-serif font-bold text-theme-primary text-xs">{item.question}</p>
            </div>

            <p className="text-theme-secondary text-xs leading-relaxed pl-5.5">
              {item.answer}
            </p>

            {item.citations.length > 0 && (
              <div className="mt-2 pt-2 border-t border-theme-border pl-5.5 space-y-1.5">
                <div className="flex items-center gap-1.5 text-[10px] uppercase font-mono font-semibold text-theme-pass">
                  <ShieldCheck className="w-3 h-3" />
                  <span>
                    {item.is_grounded
                      ? `Authoritative Citation: ${item.citations[0].policy_name}`
                      : 'Unverified — illustrative example, not retrieved evidence'}
                  </span>
                </div>
                <div className="bg-theme-panel p-2 rounded-xs border border-theme-border text-[11px] text-theme-secondary font-mono italic">
                  &ldquo;{item.citations[0].text}&rdquo;
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
