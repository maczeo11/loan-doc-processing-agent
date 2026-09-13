import React, { useState, useRef, useEffect } from 'react';
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
  Sparkles,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  FileText,
  Scale,
  RotateCcw,
} from 'lucide-react';

interface PolicyQaTabProps {
  applicationId?: string;
  onSelectEvidence?: (ev: EvidenceRef) => void;
  /** Offline archetypes have no backend policy index to query. */
  isReadOnlyPreset?: boolean;
  /**
   * This application's flagged findings. When present, the panel leads with
   * an "Explain this flag" action per finding instead of only generic policy
   * questions - the backend grounds its answer in the actual finding reason.
   */
  flaggedFindings?: Finding[];
}

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

function isFindingCitation(c: PolicyCitation): boolean {
  return c.chunk_id?.startsWith('FINDING-') ?? false;
}

const ABSTENTION_PATTERN = /ABSTENTION|UNGROUNDED CLAIM DROPPED/i;

function renderInlineCitations(text: string, keyPrefix: string): React.ReactNode {
  const parts = text.split(/(\[[A-Za-z0-9_-]+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[([A-Za-z0-9_-]+)\]$/);
    if (!match) return <React.Fragment key={`${keyPrefix}-t-${i}`}>{part}</React.Fragment>;
    const isFinding = match[1].toUpperCase().startsWith('RULE') || match[1].toUpperCase().startsWith('FINDING');
    return (
      <span
        key={`${keyPrefix}-c-${i}`}
        className={`inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded-[3px] text-[10px] font-mono font-bold align-baseline whitespace-nowrap shadow-2xs ${
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

function renderAnswerBody(answer: string, keyPrefix: string): React.ReactNode {
  const lines = answer.split('\n');
  const blocks: React.ReactNode[] = [];
  let bulletBuffer: string[] = [];

  const flushBullets = () => {
    if (bulletBuffer.length === 0) return;
    const items = bulletBuffer;
    bulletBuffer = [];
    blocks.push(
      <ul key={`${keyPrefix}-ul-${blocks.length}`} className="list-disc pl-4 space-y-1.5 my-1.5 marker:text-theme-brand">
        {items.map((b, i) => (
          <li key={i} className="text-theme-secondary text-[12px] leading-relaxed">
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
          className={`my-2 flex items-start gap-2 px-3 py-2 rounded-xs border text-[11.5px] leading-relaxed shadow-2xs ${
            isWarning
              ? 'bg-theme-unknown-bg border-theme-unknown-border text-theme-unknown'
              : 'bg-theme-panel border-theme-border text-theme-secondary'
          }`}
        >
          {isWarning && <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />}
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
    const heading = line.match(/^#{1,4}\s+(.*)$/);
    if (heading) {
      blocks.push(
        <p key={`${keyPrefix}-h-${i}`} className="text-theme-primary text-xs font-serif font-bold mt-2 mb-0.5">
          {heading[1]}
        </p>
      );
      return;
    }
    blocks.push(
      <p key={`${keyPrefix}-p-${i}`} className="text-theme-secondary text-[12px] leading-relaxed">
        {renderInlineCitations(line, `${keyPrefix}-p-${i}`)}
      </p>
    );
  });
  flushBullets();
  return <div className="space-y-1.5">{blocks}</div>;
}

const DEFAULT_SUGGESTIONS = [
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
  const [loadingStage, setLoadingStage] = useState<number>(1);
  const [history, setHistory] = useState<PolicyQaResponse[]>([]);
  const [expandedSources, setExpandedSources] = useState<Record<number, boolean>>({});
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, loading]);

  // Animated 3-stage thinking indicator during queries
  useEffect(() => {
    if (!loading) {
      setLoadingStage(1);
      return;
    }
    const timer1 = setTimeout(() => setLoadingStage(2), 700);
    const timer2 = setTimeout(() => setLoadingStage(3), 1600);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [loading]);

  const toggleSources = (idx: number) => {
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const ask = async (raw: string) => {
    const q = raw.trim();
    if (!q || loading) return;

    if (isReadOnlyPreset) {
      setHistory((prev) => [
        ...prev,
        {
          question: q,
          answer:
            'Policy retrieval runs server-side against the hybrid policy corpus. Open a live dossier to query it in real time.',
          is_grounded: false,
          citations: [],
        },
      ]);
      return;
    }

    if (!applicationId) {
      setHistory((prev) => [
        ...prev,
        {
          question: q,
          answer: 'Please select an active loan dossier before querying policy guidelines.',
          is_grounded: false,
          citations: [],
        },
      ]);
      return;
    }

    setLoading(true);
    setQuestion('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const chatHistory: ChatMessage[] = history.slice(-6).flatMap((item) => [
        { role: 'user' as const, content: item.question },
        { role: 'assistant' as const, content: item.answer },
      ]);

      const resp = await api.askQuestion(applicationId, {
        question: q,
        history: chatHistory,
      });

      const citations: PolicyCitation[] = (resp.citations || []).map((c) => ({
        chunk_id: c.chunk_id || '',
        policy_name: c.policy_id || c.title || (c.chunk_id?.startsWith('FINDING-') ? 'Application Finding' : 'Policy'),
        section: c.section || (c.page_number ? `Page ${c.page_number}` : ''),
        text: c.excerpt || c.text || c.quoted_span || '',
        score: typeof c.score === 'number' ? c.score : 0,
        document_id: c.document_id,
        document_type: c.document_type,
        page_number: c.page_number,
        bounding_box: c.bounding_box ?? null,
        is_policy: typeof c.is_policy === 'boolean' ? c.is_policy : !c.document_id,
      }));

      const isAbstained = ABSTENTION_PATTERN.test(resp.answer || '');

      setHistory((prev) => [
        ...prev,
        {
          question: q,
          answer: resp.answer,
          is_grounded: !isAbstained && citations.length > 0,
          citations,
        },
      ]);
    } catch (err: unknown) {
      setHistory((prev) => [
        ...prev,
        {
          question: q,
          answer: `Policy inquiry failed: ${
            err instanceof Error ? err.message : 'Unknown network error'
          }. Please retry.`,
          is_grounded: false,
          citations: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      ask(question);
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuestion(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 96)}px`;
  };

  return (
    <div className="h-full flex flex-col min-h-0 bg-theme-panel/40 select-text">
      {/* Top Header */}
      <div className="flex-none px-4 py-3 bg-gradient-to-r from-emerald-950 via-theme-brand to-emerald-900 border-b border-emerald-800 text-white flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-sm bg-white/15 border border-white/20 flex items-center justify-center text-emerald-200 shrink-0 shadow-inner">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-serif font-bold tracking-wide text-white truncate">
                FinScan AI Assistant
              </span>
              <span className="flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-emerald-400/20 border border-emerald-400/40 text-emerald-200 font-bold uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Grounded RAG
              </span>
            </div>
            <p className="text-[10px] text-emerald-100/70 font-mono truncate">
              Deterministic Credit Policy &amp; Evidence Cross-Examiner
            </p>
          </div>
        </div>

        {history.length > 0 && (
          <button
            type="button"
            onClick={() => setHistory([])}
            className="flex items-center gap-1 px-2 py-1 rounded-xs text-[10.5px] font-mono text-emerald-200 hover:text-white bg-white/10 hover:bg-white/20 border border-white/20 transition-all cursor-pointer shadow-xs"
            title="Clear inquiry thread"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Flagged Audit Item Fast-Actions */}
      {flaggedFindings.length > 0 && (
        <div className="flex-none px-3.5 py-2.5 bg-rose-50/80 border-b border-rose-200/80">
          <div className="flex items-center justify-between gap-1.5 mb-1.5 text-[10px] font-mono font-bold text-rose-900 uppercase tracking-wider">
            <div className="flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-700" />
              <span>Priority Discrepancies ({flaggedFindings.length})</span>
            </div>
            <span className="text-[9.5px] text-rose-700/80 font-normal lowercase">click to analyze</span>
          </div>
          <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-none">
            {flaggedFindings.map((f) => (
              <button
                key={f.rule_id}
                type="button"
                onClick={() =>
                  ask(
                    `Why was this application flagged under ${f.rule_id} (${f.rule_name})? State the discrepancy, tolerance, and policy requirement.`
                  )
                }
                disabled={loading}
                className="shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-xs bg-white hover:bg-rose-50 border border-rose-300 hover:border-rose-500 text-[11px] font-mono font-bold text-rose-900 transition-all disabled:opacity-50 cursor-pointer shadow-xs group"
              >
                <span>⚡ {f.rule_name}</span>
                <span className="text-[9.5px] px-1 py-0.2 bg-rose-100 text-rose-800 border border-rose-200 rounded-xs font-mono">
                  {f.rule_id}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Scrollable Message Thread */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 bg-amber-50/20">
        {/* Empty State / Suggested Prompts */}
        {history.length === 0 && !loading && (
          <div className="p-5 rounded-sm bg-white border border-stone-300 space-y-4 shadow-sm">
            <div className="flex items-center gap-2.5 text-xs font-serif font-bold text-stone-900 border-b border-stone-200 pb-2.5">
              <div className="w-5 h-5 rounded-xs bg-theme-brand text-white flex items-center justify-center">
                <BookOpen className="w-3.5 h-3.5" />
              </div>
              <span className="text-[13px]">Institutional Underwriting Copilot</span>
            </div>
            <p className="text-[12px] text-stone-700 leading-relaxed font-sans">
              Query debt-to-income limits, salary variance tolerances, mandatory documentation mandates, or specific applicant transactions. Every response is verified against the hybrid retrieval policy index and dossier facts.
            </p>
            <div className="space-y-2 pt-1">
              <span className="text-[10.5px] font-mono uppercase tracking-widest text-stone-700 font-bold">
                Suggested Policy Queries:
              </span>
              <div className="flex flex-col gap-2">
                {DEFAULT_SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => ask(suggestion)}
                    disabled={loading}
                    className="text-left px-3.5 py-2.5 rounded-sm bg-stone-50 hover:bg-emerald-50/80 border border-stone-300 hover:border-theme-brand text-[11.5px] font-mono font-medium text-stone-900 hover:text-theme-brand transition-all disabled:opacity-50 cursor-pointer flex items-center justify-between gap-2 shadow-xs group"
                  >
                    <span>{suggestion}</span>
                    <span className="text-stone-400 group-hover:text-theme-brand transition-colors text-xs font-bold shrink-0">
                      ↵ Query
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Message Exchange List */}
        {history.map((item, idx) => {
          const sourceCount = item.citations.length;
          const isExpanded = expandedSources[idx] ?? true;
          return (
            <div key={idx} className="space-y-3">
              {/* Reviewer / Underwriter Question Bubble */}
              <div className="flex justify-end items-start gap-2">
                <div className="max-w-[85%] rounded-md bg-stone-900 text-white px-4 py-2.5 text-xs shadow-md border border-stone-800">
                  <div className="text-[9.5px] font-mono text-emerald-400 uppercase font-bold tracking-wider mb-1 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <span>Underwriter Inquiry</span>
                  </div>
                  <p className="leading-relaxed font-sans text-[12.5px] text-stone-100 font-medium">{item.question}</p>
                </div>
              </div>

              {/* FinScan AI Analysis Response */}
              <div className="rounded-sm bg-white border-2 border-stone-300/90 text-xs overflow-hidden shadow-sm">
                {/* Response Meta Header */}
                <div className="px-3.5 py-2.5 bg-stone-100 border-b border-stone-300 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-xs bg-theme-brand text-white flex items-center justify-center font-bold text-[10px] shadow-xs">
                      AI
                    </div>
                    <span className="font-serif font-bold text-[12px] text-stone-900">
                      FinScan Verified Finding
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => copyToClipboard(item.answer, idx)}
                      className="flex items-center gap-1 text-[10.5px] font-mono font-bold text-stone-700 hover:text-stone-900 px-2 py-0.5 rounded-xs bg-white border border-stone-300 hover:bg-stone-50 transition-colors cursor-pointer shadow-xs"
                      title="Copy memo text to clipboard"
                    >
                      {copiedIndex === idx ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-700" />
                          <span className="text-emerald-700">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 text-stone-600" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>

                    <div
                      className={`flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-xs border ${
                        item.is_grounded
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                          : 'bg-amber-50 text-amber-800 border-amber-300'
                      }`}
                    >
                      {item.is_grounded ? (
                        <>
                          <ShieldCheck className="w-3 h-3" />
                          <span>Grounded</span>
                        </>
                      ) : (
                        <>
                          <ShieldAlert className="w-3 h-3" />
                          <span>Unverified</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Response Text Body */}
                <div className="p-3.5 space-y-3">
                  {renderAnswerBody(sanitizePiiInText(item.answer), `qa-${idx}`)}

                  {/* Collapsible Verified Citations Tray */}
                  {sourceCount > 0 && (
                    <div className="pt-2 border-t border-theme-border/80">
                      <button
                        type="button"
                        onClick={() => toggleSources(idx)}
                        className="w-full flex items-center justify-between text-[10.5px] font-mono font-bold uppercase tracking-wider text-theme-secondary hover:text-theme-primary transition-colors py-1 cursor-pointer"
                      >
                        <span className="flex items-center gap-1.5">
                          <span>Verified Citations ({sourceCount})</span>
                          <span className="text-[9.5px] font-normal text-theme-muted lowercase">
                            · traceable evidence
                          </span>
                        </span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>

                      {isExpanded && (
                        <div className="mt-2 space-y-2">
                          {item.citations.map((c, cIdx) => {
                            const ev = toEvidenceRef(c);
                            const fromFinding = isFindingCitation(c);
                            const isDoc = !c.is_policy && !!c.document_id;
                            const badgeBorder = fromFinding
                              ? 'border-l-4 border-l-rose-600 bg-rose-50/40'
                              : isDoc
                              ? 'border-l-4 border-l-emerald-600 bg-emerald-50/40'
                              : 'border-l-4 border-l-stone-700 bg-stone-50';

                            return (
                              <div
                                key={cIdx}
                                className={`p-2.5 rounded-sm border border-stone-300 ${badgeBorder} shadow-xs space-y-1`}
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <div className="flex items-center gap-1.5 min-w-0 font-mono text-[11px] font-bold text-stone-900 truncate">
                                    {isDoc ? (
                                      <FileText className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
                                    ) : fromFinding ? (
                                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                                    ) : (
                                      <Scale className="w-3.5 h-3.5 text-stone-700 shrink-0" />
                                    )}
                                    <span className="truncate">{c.policy_name}</span>
                                    {c.section && (
                                      <span className="text-stone-500 font-normal shrink-0">
                                        · {c.section}
                                      </span>
                                    )}
                                  </div>

                                  {ev && onSelectEvidence && (
                                    <button
                                      type="button"
                                      onClick={() => onSelectEvidence(ev)}
                                      className="shrink-0 flex items-center gap-1 text-[10.5px] font-mono font-bold text-emerald-800 hover:text-emerald-950 bg-emerald-100/70 hover:bg-emerald-200/90 border border-emerald-300 px-2 py-0.5 rounded-xs transition-colors cursor-pointer shadow-2xs"
                                      title="Jump to PDF coordinates"
                                    >
                                      <span>View Page {ev.page_number}</span>
                                      <ExternalLink className="w-3 h-3" />
                                    </button>
                                  )}
                                </div>

                                {c.text && (
                                  <p className="text-[11px] font-mono text-stone-700 leading-snug line-clamp-2 bg-white/80 p-1.5 rounded-xs border border-stone-200">
                                    &ldquo;{sanitizePiiInText(c.text.trim())}&rdquo;
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Loading Thinking Stage State */}
        {loading && (
          <div className="p-4 rounded-sm bg-stone-900 text-white border border-stone-800 space-y-3 shadow-md animate-fade-in">
            <div className="flex items-center gap-2.5 text-xs font-serif font-bold text-emerald-400">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Cross-Referencing Policy &amp; Dossier...</span>
            </div>

            <div className="space-y-1.5 text-[11px] font-mono">
              <div
                className={`flex items-center gap-2 ${
                  loadingStage >= 1 ? 'text-emerald-400 font-bold' : 'text-stone-500'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                <span>1. Lexical BM25 + Dense BGE Vector Retrieval (RRF Fusion)</span>
              </div>
              <div
                className={`flex items-center gap-2 ${
                  loadingStage >= 2 ? 'text-emerald-400 font-bold' : 'text-stone-500'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                <span>2. Cross-referencing Stated vs. Extracted Dossier Facts</span>
              </div>
              <div
                className={`flex items-center gap-2 ${
                  loadingStage >= 3 ? 'text-emerald-400 font-bold' : 'text-stone-500'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                <span>3. Enforcing Zero-Hallucination Grounding Firewall</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Sticky Bottom Input Bar with High Contrast Border and Button */}
      <div className="flex-none p-3.5 bg-stone-100 border-t-2 border-stone-300 shadow-sm">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
          className="relative flex items-end gap-2 bg-white border-2 border-stone-400 rounded-sm p-2 shadow-sm focus-within:border-theme-brand focus-within:ring-2 focus-within:ring-theme-brand/20 transition-all"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={question}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask policy guidelines, discrepancies, or verify applicant facts..."
            aria-label="Ask underwriter research question"
            disabled={loading}
            className="flex-1 bg-transparent border-none text-xs text-stone-900 placeholder-stone-400 focus:outline-none resize-none py-1 px-2 leading-relaxed max-h-24 font-sans disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            aria-label="Submit inquiry"
            className="p-2 rounded-xs bg-theme-brand text-white hover:bg-emerald-900 disabled:bg-stone-200 disabled:text-stone-400 disabled:opacity-50 transition-all cursor-pointer shrink-0 shadow-sm font-bold"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </form>

        <div className="flex items-center justify-between px-1.5 pt-2 text-[10px] font-mono text-stone-600 font-medium">
          <span>Enter ↵ to send · Shift+Enter for newline</span>
          <span className="text-emerald-800 font-bold">Dual RAG: Policy Corpus + Dossier Facts</span>
        </div>
      </div>
    </div>
  );
};
