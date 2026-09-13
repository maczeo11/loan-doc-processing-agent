import React, { useState } from 'react';
import { api } from '../../services/api';
import { PolicyQaResponse, PolicyCitation } from '../../types/api';
import { EvidenceRef } from '../../types/evidence';
import { Finding, ChatMessage } from '../../types/contracts';
import { sanitizePiiInText } from '../../utils/pii';
import {
  Send,
  BookOpen,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  ExternalLink,
  AlertTriangle,
  MessageCircleQuestion,
  Sparkles,
  X,
} from 'lucide-react';

interface PolicyQaTabProps {
  applicationId?: string;
  onSelectEvidence?: (ev: EvidenceRef) => void;
  /** Offline archetypes have no backend policy index to query. */
  isReadOnlyPreset?: boolean;
  /**
   * This application's flagged findings. When present, the panel leads with
   * an "Explain this flag" action per finding instead of only generic policy
   * questions - the backend (apps/api/routes/review.py) grounds its answer in
   * the actual deterministic finding reason plus relevant policy, so this is
   * a real explanation of why the application was flagged/rejected, not a
   * canned message.
   */
  flaggedFindings?: Finding[];
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

/** A citation sourced from this application's own findings, not the policy corpus. */
function isFindingCitation(c: PolicyCitation): boolean {
  return c.chunk_id?.startsWith('FINDING-') ?? false;
}

const ABSTENTION_PATTERN = /ABSTENTION|UNGROUNDED CLAIM DROPPED/i;

/**
 * Renders a `[TAG]` citation marker inline as a small pill instead of literal
 * brackets in running prose — the raw text is still fully present (nothing is
 * hidden), it just reads as a reference instead of noise.
 */
function renderInlineCitations(text: string, keyPrefix: string): React.ReactNode {
  const parts = text.split(/(\[[A-Za-z0-9_-]+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[([A-Za-z0-9_-]+)\]$/);
    if (!match) return <React.Fragment key={`${keyPrefix}-t-${i}`}>{part}</React.Fragment>;
    const isFinding = match[1].toUpperCase().startsWith('RULE') || match[1].toUpperCase().startsWith('FINDING');
    return (
      <span
        key={`${keyPrefix}-c-${i}`}
        className={`inline-flex items-center px-1 py-[1px] mx-0.5 rounded-[3px] text-[9.5px] font-mono font-semibold align-baseline whitespace-nowrap ${
          isFinding
            ? 'bg-theme-flag-bg text-theme-flag border border-theme-flag-border'
            : 'bg-theme-brand/10 text-theme-brand border border-theme-brand/20'
        }`}
      >
        {match[1]}
      </span>
    );
  });
}

/**
 * Turns the raw answer string into readable blocks instead of one flat run-on
 * paragraph: `- ` lines become a real bullet list, `> ` lines (the grounding
 * firewall's own ABSTENTION / UNGROUNDED CLAIM DROPPED notices,
 * core/rag/grounding.py) become a distinct warning callout, everything else
 * stays plain prose — all with inline citation pills.
 */
function renderAnswerBody(answer: string, keyPrefix: string): React.ReactNode {
  const lines = answer.split('\n');
  const blocks: React.ReactNode[] = [];
  let bulletBuffer: string[] = [];

  const flushBullets = () => {
    if (bulletBuffer.length === 0) return;
    const items = bulletBuffer;
    bulletBuffer = [];
    blocks.push(
      <ul key={`${keyPrefix}-ul-${blocks.length}`} className="list-disc pl-4 space-y-1 my-1 marker:text-theme-muted">
        {items.map((b, i) => (
          <li key={i} className="text-theme-secondary text-xs leading-relaxed">
            {renderInlineCitations(b, `${keyPrefix}-b-${blocks.length}-${i}`)}
          </li>
        ))}
      </ul>
    );
  };

  lines.forEach((rawLine, i) => {
    const line = rawLine.trim();
    if (!line) {
      flushBullets();
      return;
    }
    if (line.startsWith('>')) {
      flushBullets();
      const content = line.replace(/^>\s*⚠️?\s*/, '');
      const isWarning = ABSTENTION_PATTERN.test(content);
      blocks.push(
        <div
          key={`${keyPrefix}-q-${i}`}
          className={`my-1.5 flex items-start gap-1.5 px-2.5 py-2 rounded-xs border text-[11px] leading-relaxed ${
            isWarning
              ? 'bg-theme-unknown-bg border-theme-unknown-border text-theme-unknown'
              : 'bg-theme-panel border-theme-border text-theme-secondary'
          }`}
        >
          {isWarning && <ShieldAlert className="w-3 h-3 flex-shrink-0 mt-0.5" />}
          <span>{renderInlineCitations(content, `${keyPrefix}-q-${i}`)}</span>
        </div>
      );
      return;
    }
    if (/^[-*]\s+/.test(line)) {
      bulletBuffer.push(line.replace(/^[-*]\s+/, ''));
      return;
    }
    flushBullets();
    // Markdown heading noise ("### Credit Appraisal Memo") reads better as a
    // small bold label than literal hash marks in a chat answer.
    const heading = line.match(/^#{1,4}\s+(.*)$/);
    if (heading) {
      blocks.push(
        <p key={`${keyPrefix}-h-${i}`} className="text-theme-primary text-xs font-serif font-bold mt-1">
          {heading[1]}
        </p>
      );
      return;
    }
    blocks.push(
      <p key={`${keyPrefix}-p-${i}`} className="text-theme-secondary text-xs leading-relaxed">
        {renderInlineCitations(line, `${keyPrefix}-p-${i}`)}
      </p>
    );
  });
  flushBullets();
  return <div className="space-y-1">{blocks}</div>;
}

/**
 * Prompts, not answers.
 *
 * This panel previously opened with a fabricated "±5.0% / 50% DTI" answer and a
 * citation to a policy section that had never been retrieved. Even flagged
 * unverified, a made-up threshold sitting in the answer stream is exactly the
 * hallucination this product exists to prevent — so the empty state now offers
 * questions to ask instead of pre-filled conclusions.
 */
const SUGGESTED_QUESTIONS = [
  'What is the salary reconciliation variance tolerance?',
  'What is the maximum permitted debt-to-income ratio?',
  'Which documents are mandatory for retail loan underwriting?',
];

export const PolicyQaTab: React.FC<PolicyQaTabProps> = ({
  applicationId,
  onSelectEvidence,
  isReadOnlyPreset = false,
  flaggedFindings = [],
}) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<PolicyQaResponse[]>([]);

  const ask = async (raw: string) => {
    const q = raw.trim();
    if (!q || loading) return;

    if (isReadOnlyPreset) {
      setHistory((prev) => [
        {
          question: q,
          answer:
            'Policy retrieval runs server-side against the policy corpus. Open a live dossier to query it.',
          is_grounded: false,
          citations: [],
        },
        ...prev,
      ]);
      return;
    }

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
      // Build previous message history from existing conversation (chronological order)
      const chatHistory: ChatMessage[] = [...history].reverse().slice(-6).flatMap((item) => [
        { role: 'user' as const, content: item.question },
        { role: 'assistant' as const, content: item.answer },
      ]);

      const resp = await api.askQuestion(applicationId, {
        question: q,
        history: chatHistory,
      });
      const citations: PolicyCitation[] = (resp.citations || []).map((c) => ({
        chunk_id: c.chunk_id || '',
        // A finding-sourced citation (chunk_id "FINDING-RULE-ID-XX", see
        // apps/api/routes/review.py::_finding_evidence_citations) has no
        // policy_id - label it as the application finding it is, not "Policy".
        policy_name: c.policy_id || c.title || (c.chunk_id?.startsWith('FINDING-') ? 'Application Finding' : 'Policy'),
        section: c.section || (c.page_number ? `Page ${c.page_number}` : ''),
        text: c.excerpt || c.text || c.quoted_span || '',
        score: typeof c.score === 'number' ? c.score : 0,
        document_id: c.document_id,
        document_type: c.document_type,
        page_number: c.page_number,
        bounding_box: c.bounding_box ?? null,
      }));

      // Trust the answer text itself, not just whether citations came back:
      // the backend firewall (core/rag/grounding.py::sanitize_summary_text)
      // can withhold an answer with an ABSTENTION notice even when `hits`
      // (and therefore `citations`) were non-empty - grounded means the
      // ANSWER cited something real, not merely that retrieval found something.
      const isAbstained = ABSTENTION_PATTERN.test(resp.answer || '');

      setHistory((prev) => [
        {
          question: q,
          answer: resp.answer,
          is_grounded: !isAbstained && citations.length > 0,
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    ask(question);
  };

  return (
    <div className="space-y-3.5">
      {/* Ask Input */}
      <form onSubmit={handleSubmit} className="relative">
        <MessageCircleQuestion className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-theme-muted pointer-events-none" />
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask policy guidelines or why a finding was flagged..."
          aria-label="Ask a policy or findings question"
          className="w-full bg-theme-card border border-theme-border rounded-xs py-2 pl-8 pr-9 text-xs text-theme-primary placeholder-theme-muted focus:outline-none focus:border-theme-brand shadow-xs transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          aria-label="Submit question"
          className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 text-theme-muted hover:text-theme-primary disabled:opacity-40 transition-opacity cursor-pointer"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
      </form>

      {/* Flagged findings: lead with a direct "explain this" action per flag
          rather than making the reviewer discover it's possible via the
          generic question box. The backend grounds the answer in this
          application's own finding reason + relevant policy, not a canned
          restatement. */}
      {flaggedFindings.length > 0 && (
        <div className="p-3.5 rounded-xs bg-theme-flag-bg border border-theme-flag-border space-y-2">
          <div className="flex items-center gap-1.5 text-[10px] uppercase font-mono font-bold text-theme-flag tracking-wider">
            <AlertTriangle className="w-3 h-3" />
            <span>
              {flaggedFindings.length} flagged {flaggedFindings.length === 1 ? 'finding' : 'findings'} — ask why
            </span>
          </div>
          <div className="flex flex-col gap-1">
            {flaggedFindings.map((f) => (
              <button
                key={f.rule_id}
                type="button"
                onClick={() => ask(`Why was this application flagged for ${f.rule_name} (${f.rule_id})? Explain the reason and the policy basis.`)}
                disabled={loading}
                className="group text-left flex items-center justify-between gap-2 px-2 py-1.5 rounded-xs hover:bg-theme-card/60 transition-colors disabled:opacity-50"
              >
                <span className="text-[11px] font-mono text-theme-flag truncate">
                  Explain: {f.rule_name}
                </span>
                <Sparkles className="w-3 h-3 text-theme-flag/60 group-hover:text-theme-flag flex-shrink-0" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Empty state: offer questions, never a pre-filled answer. */}
      {history.length === 0 && !loading && (
        <div className="p-3.5 rounded-xs bg-theme-panel border border-theme-border space-y-2">
          <div className="flex items-center gap-1.5 text-[10px] uppercase font-mono font-bold text-theme-muted tracking-wider">
            <BookOpen className="w-3 h-3" />
            <span>Grounded policy &amp; findings retrieval</span>
          </div>
          <p className="text-[11px] text-theme-secondary leading-relaxed">
            Answers quote retrieved policy passages and this application's own findings with
            citations. Nothing is asserted without one.
          </p>
          <div className="flex flex-col gap-1.5 pt-0.5">
            {SUGGESTED_QUESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => ask(suggestion)}
                disabled={loading}
                className="text-left text-[11px] font-mono text-theme-brand hover:underline disabled:opacity-50"
              >
                → {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Q&A Stream */}
      <div className="space-y-3">
        {loading && (
          <div className="p-3.5 rounded-xs bg-theme-card border border-theme-border shadow-xs text-xs space-y-2 animate-pulse">
            <div className="flex items-center gap-1.5 text-theme-muted">
              <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0" />
              <span className="text-[11px] font-mono">Retrieving policy &amp; findings…</span>
            </div>
          </div>
        )}

        {history.map((item, idx) => {
          const sourceCount = item.citations.length;
          return (
            <div
              key={idx}
              className="rounded-xs bg-theme-card border border-theme-border shadow-xs text-xs overflow-hidden"
            >
              {/* Question header */}
              <div className="flex items-start gap-2 px-3.5 pt-3 pb-2 bg-theme-panel/60 border-b border-theme-border">
                <span className="flex-shrink-0 w-[18px] h-[18px] rounded-full bg-theme-brand text-white text-[9px] font-mono font-bold flex items-center justify-center mt-0.5">
                  Q
                </span>
                <p className="font-serif font-bold text-theme-primary text-xs leading-snug">{item.question}</p>
              </div>

              {/* Answer body */}
              <div className="px-3.5 pt-2.5 pb-3 space-y-2">
                <div className="pl-6">{renderAnswerBody(sanitizePiiInText(item.answer), `qa-${idx}`)}</div>

                {/* Grounding banner */}
                <div className="pt-2 border-t border-theme-border pl-6 space-y-1.5">
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
                        ? `Grounded — ${sourceCount} source${sourceCount === 1 ? '' : 's'} cited`
                        : 'Unverified — not asserted as evidence-backed'}
                    </span>
                  </div>

                  {sourceCount > 0 && (
                    <div className="flex flex-col gap-1.5">
                      {item.citations.map((c, cIdx) => {
                        const ev = toEvidenceRef(c);
                        const fromFinding = isFindingCitation(c);
                        const accent = fromFinding
                          ? 'border-l-2 border-l-theme-flag'
                          : 'border-l-2 border-l-theme-brand';
                        const body = (
                          <>
                            <div className="text-[10px] font-mono text-theme-muted mb-1 flex items-center gap-1.5">
                              {fromFinding ? (
                                <AlertTriangle className="w-2.5 h-2.5 text-theme-flag flex-shrink-0" />
                              ) : (
                                <BookOpen className="w-2.5 h-2.5 text-theme-brand flex-shrink-0" />
                              )}
                              <span className="truncate">{c.policy_name}{c.section ? ` · ${c.section}` : ''}</span>
                            </div>
                            {c.text && (
                              <span className="italic text-theme-secondary">&ldquo;{sanitizePiiInText(c.text)}&rdquo;</span>
                            )}
                          </>
                        );

                        // Navigable citations become jump targets into the PDF canvas.
                        return ev && onSelectEvidence ? (
                          <button
                            key={cIdx}
                            type="button"
                            onClick={() => onSelectEvidence(ev)}
                            title="Click to jump and highlight on PDF canvas"
                            className={`w-full text-left bg-theme-panel hover:bg-theme-card p-2 rounded-xs border border-theme-border hover:border-theme-border-card ${accent} text-[11px] text-theme-secondary font-mono transition-colors cursor-pointer flex items-start justify-between gap-2`}
                          >
                            <span className="min-w-0 flex-1">{body}</span>
                            <ExternalLink className="w-3 h-3 text-theme-muted flex-shrink-0 mt-0.5" />
                          </button>
                        ) : (
                          <div
                            key={cIdx}
                            className={`bg-theme-panel p-2 rounded-xs border border-theme-border ${accent} text-[11px] text-theme-secondary font-mono`}
                          >
                            {body}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {history.length > 0 && (
        <button
          type="button"
          onClick={() => setHistory([])}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 text-[10px] uppercase font-mono font-semibold text-theme-muted hover:text-theme-secondary transition-colors"
        >
          <X className="w-3 h-3" />
          Clear conversation
        </button>
      )}
    </div>
  );
};
