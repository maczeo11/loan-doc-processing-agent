import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Loader2,
  AlertCircle,
  FileCheck2,
  BookOpen,
  RotateCcw,
  Sparkles,
  User,
  ShieldCheck,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import { api } from '../../services/api';
import { useEvidenceNavigation } from '../../context/EvidenceNavigationContext';
import type { Citation, EvidenceRef, QuestionResponse } from '../../types/contracts';

interface QaPanelProps {
  applicationId: string;
  isDemoMode?: boolean;
}

interface QaMessage {
  id: string;
  question: string;
  answer?: string;
  citations?: Citation[];
  timestamp: string;
  isLoading?: boolean;
  error?: string | null;
}

const SAMPLE_QUESTIONS = [
  'Does stated net salary match bank deposits within 5% tolerance?',
  'Are all 5 mandatory dossier documents verified?',
  'How does annualized gross salary compare to ITR-V income?',
  'Were any bounced transactions found in the bank statement?',
];

function getDemoAnswerForQuery(query: string): QuestionResponse {
  const q = query.toLowerCase();

  if (q.includes('salary') || q.includes('payroll') || q.includes('deposit') || q.includes('credit') || q.includes('net') || q.includes('gross')) {
    return {
      answer:
        'Stated payslip net salary (₹72,500.00) from Tech Mahindra Ltd is corroborated by consistent bank payroll credit on 31-AUG-2026 (₹72,500.00). Variance is 0.0%, which is well within the 5.0% underwriting policy tolerance (RULE-INC-01: PASS).',
      citations: [
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
        {
          policy_id: 'POL-INC-02',
          section: 'Section 4.1: Net Income Reconciliation',
          title: 'Payroll Deposit Verification Tolerance',
        },
      ],
    };
  }

  if (q.includes('tax') || q.includes('itr') || q.includes('annual') || q.includes('income')) {
    return {
      answer:
        "The applicant's annualized payslip gross income (12 × ₹85,000.00 = ₹10,20,000.00) perfectly matches the Gross Total Income reported on ITR-V acknowledgement for AY 2024-25 (₹10,20,000.00). Total tax paid is verified at ₹78,000.00 (RULE-TAX-01: PASS).",
      citations: [
        {
          document_id: 'doc-itr-v',
          document_type: 'tax_return',
          page_number: 1,
          quoted_span: 'Gross Total Income: 10,20,000',
          bounding_box: { x0: 0.295, y0: 0.347, x1: 0.631, y1: 0.363 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
        {
          document_id: 'doc-payslip-aug',
          document_type: 'payslip',
          page_number: 1,
          quoted_span: 'Gross Earnings: 85,000.00',
          bounding_box: { x0: 0.295, y0: 0.371, x1: 0.565, y1: 0.386 },
          confidence: 0.99,
          extraction_method: 'pymupdf_native',
        },
      ],
    };
  }

  if (q.includes('pan') || q.includes('identity') || q.includes('name') || q.includes('aadhaar') || q.includes('kyc')) {
    return {
      answer:
        'Applicant identity for "Ananya Sharma" and PAN "ABCPS4821K" (masked as XXXXXX4821) have been reconciled across the PAN Card, ITR-V, Bank Statement, and Payslips with zero discrepancies detected (RULE-ID-01: PASS).',
      citations: [
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
    };
  }

  if (q.includes('document') || q.includes('mandatory') || q.includes('complete') || q.includes('category') || q.includes('missing')) {
    return {
      answer:
        'All 5 required document categories are present and verified in the dossier: Loan Application Form, 3 consecutive payslips (June, July, August 2026), 6-month HDFC bank statement, ITR-V acknowledgement, and PAN card identity proof (RULE-COMP-01: PASS).',
      citations: [
        {
          document_id: 'doc-app-form',
          document_type: 'application_form',
          page_number: 1,
          quoted_span: 'Loan Application Form - Verified',
          confidence: 0.95,
          extraction_method: 'pymupdf_native',
        },
        {
          policy_id: 'POL-COMP-01',
          section: 'Section 2.1: Minimum Dossier Documentation Checklist',
          title: 'Retail Credit Dossier Mandate',
        },
      ],
    };
  }

  if (q.includes('bounce') || q.includes('bounced') || q.includes('balance') || q.includes('hdfc')) {
    return {
      answer:
        'HDFC Bank Statement shows 0 inward/outward bounced transactions over the 6-month period and a closing balance of ₹1,45,000.00 as of August 31, 2026. Account meets liquidity guidelines.',
      citations: [
        {
          document_id: 'doc-bank-stmt',
          document_type: 'bank_statement',
          page_number: 3,
          quoted_span: 'Closing Balance: 1,45,000.00',
          bounding_box: { x0: 0.295, y0: 0.157, x1: 0.631, y1: 0.173 },
          confidence: 0.97,
          extraction_method: 'pymupdf_native',
        },
      ],
    };
  }

  return {
    answer:
      `Underwriting evaluation for application ${query ? `regarding "${query}"` : 'dossier'}: Verified monthly net income of ₹72,500 aligns with bank deposits. Annual gross income of ₹10,20,000 aligns with tax filings. All required documents are verified and within policy tolerances. Ready for underwriter sign-off.`,
    citations: [
      {
        document_id: 'doc-payslip-aug',
        document_type: 'payslip',
        page_number: 1,
        quoted_span: 'Net Pay: 72,500.00',
        bounding_box: { x0: 0.295, y0: 0.56, x1: 0.52, y1: 0.576 },
        confidence: 0.99,
        extraction_method: 'pymupdf_native',
      },
    ],
  };
}

export const QaPanel: React.FC<QaPanelProps> = ({ applicationId, isDemoMode = false }) => {
  const { navigateToEvidence } = useEvidenceNavigation();
  const [query, setQuery] = useState<string>('');
  const [history, setHistory] = useState<QaMessage[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [history, isSubmitting]);

  const handleCitationClick = (citation: Citation) => {
    if (!citation.document_id || !citation.page_number) return;

    const evidenceRef: EvidenceRef = {
      document_id: citation.document_id,
      document_type: citation.document_type || 'document',
      page_number: citation.page_number,
      quoted_span: citation.quoted_span || citation.text || '',
      bounding_box: citation.bounding_box || undefined,
      extraction_method: citation.extraction_method || 'rag_citation',
      confidence: citation.confidence ?? 1.0,
    };

    navigateToEvidence(evidenceRef);
  };

  const handleAsk = async (questionText?: string) => {
    const textToAsk = (questionText || query).trim();
    if (!textToAsk || isSubmitting) return;

    setApiError(null);
    const messageId = `qa-${Date.now()}`;
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newEntry: QaMessage = {
      id: messageId,
      question: textToAsk,
      timestamp,
      isLoading: true,
    };

    setHistory((prev) => [...prev, newEntry]);
    setQuery('');
    setIsSubmitting(true);

    try {
      let response: QuestionResponse;

      if (isDemoMode) {
        // Deterministic realistic delay to mimic hybrid retrieval + grounding gate
        await new Promise((resolve) => setTimeout(resolve, 350));
        response = getDemoAnswerForQuery(textToAsk);
      } else {
        // Live API call: POST /applications/{id}/questions
        response = await api.askQuestion(applicationId, { question: textToAsk });
      }

      setHistory((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                answer: response.answer,
                citations: response.citations || [],
                isLoading: false,
              }
            : msg
        )
      );
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to query underwriting policy Q&A.';
      setApiError(errorMsg);
      setHistory((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                error: errorMsg,
                isLoading: false,
              }
            : msg
        )
      );
    } finally {
      setIsSubmitting(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  const handleClearHistory = () => {
    setHistory([]);
    setApiError(null);
  };

  return (
    <div className="flex flex-col h-full bg-white text-xs">
      {/* Policy Q&A Header Banner */}
      <div className="px-3.5 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-slate-800">Policy & Grounding Q&A</span>
              <span
                className={`text-[9px] font-mono font-semibold px-1.5 py-0.2 rounded border ${
                  isDemoMode
                    ? 'bg-amber-50 text-amber-800 border-amber-200'
                    : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                }`}
              >
                {isDemoMode ? 'DEMO RAG' : 'LIVE API'}
              </span>
            </div>
          </div>
        </div>

        {history.length > 0 && (
          <button
            type="button"
            onClick={handleClearHistory}
            className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 p-1 rounded hover:bg-slate-200/60 transition-colors"
            title="Clear Q&A inquiry history"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Global Error Banner */}
      {apiError && (
        <div className="mx-3 mt-2 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2 shrink-0">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <span className="font-bold block">API Request Error</span>
            <span className="text-[11px] leading-snug break-all">{apiError}</span>
          </div>
          <button
            type="button"
            onClick={() => setApiError(null)}
            className="text-rose-500 hover:text-rose-700 font-bold ml-1 text-sm leading-none"
          >
            ×
          </button>
        </div>
      )}

      {/* Main Q&A Messages Area */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {history.length === 0 ? (
          /* Empty State: Banking Guidelines */
          <div className="py-6 px-3 flex flex-col items-center text-center space-y-3">
            <div className="w-10 h-10 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="space-y-1 max-w-xs">
              <h4 className="font-bold text-slate-800 text-xs">Grounded Underwriting Inquiries</h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Query loan policy thresholds, income reconciliation math, or document provenance. All
                answers cite retrieved evidence chunks.
              </p>
            </div>

            {/* Quick Prompts */}
            <div className="w-full pt-2 space-y-1.5 text-left">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block px-1">
                Suggested Inquiries:
              </span>
              {SAMPLE_QUESTIONS.map((sampleQ, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleAsk(sampleQ)}
                  className="w-full text-left p-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-indigo-50 hover:border-indigo-300 text-[11px] text-slate-700 hover:text-indigo-900 transition-colors flex items-center justify-between group shadow-2xs"
                >
                  <span className="truncate pr-2">{sampleQ}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 shrink-0" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Active History List */
          history.map((msg) => (
            <div key={msg.id} className="space-y-2">
              {/* Question Card (Reviewer) */}
              <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50 space-y-1 shadow-2xs">
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span className="font-bold text-slate-700 uppercase flex items-center gap-1">
                    <User className="w-3 h-3 text-slate-500" />
                    Reviewer Query
                  </span>
                  <span>{msg.timestamp}</span>
                </div>
                <p className="text-xs font-semibold text-slate-900 leading-snug">{msg.question}</p>
              </div>

              {/* Answer Card (Grounded RAG) */}
              <div className="p-3 rounded-lg border border-indigo-100 bg-indigo-50/30 space-y-2 shadow-2xs">
                <div className="flex items-center justify-between text-[10px] text-indigo-700 font-mono">
                  <span className="font-bold uppercase flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                    Grounded Analysis
                  </span>
                  <span className="text-slate-400">POST /questions</span>
                </div>

                {msg.isLoading ? (
                  <div className="py-3 flex items-center gap-2 text-indigo-700">
                    <Loader2 className="w-4 h-4 animate-spin shrink-0 text-indigo-600" />
                    <span className="text-[11px] font-medium">Retrieving policy and validating citations...</span>
                  </div>
                ) : msg.error ? (
                  <div className="text-rose-700 text-[11px] bg-rose-50 p-2 rounded border border-rose-200">
                    {msg.error}
                  </div>
                ) : (
                  <>
                    <p className="text-xs text-slate-800 leading-relaxed whitespace-pre-line font-sans">
                      {msg.answer}
                    </p>

                    {/* Citations List */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="pt-2 border-t border-indigo-100/80 space-y-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                          Verified Citations ({msg.citations.length}):
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((cit, cIdx) => {
                            const hasDocProvenance = Boolean(cit.document_id && cit.page_number);

                            if (hasDocProvenance) {
                              return (
                                <button
                                  key={cIdx}
                                  type="button"
                                  onClick={() => handleCitationClick(cit)}
                                  className="inline-flex items-center gap-1.5 font-mono text-[10px] px-2 py-1 rounded-md border border-indigo-200 bg-white text-indigo-700 hover:bg-indigo-50 hover:border-indigo-400 transition-all shadow-2xs cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-400"
                                  title={`Inspect citation in ${cit.document_id} on Page ${cit.page_number}`}
                                >
                                  <FileCheck2 className="w-3 h-3 text-indigo-600 shrink-0" />
                                  <span className="font-bold">{cit.document_id}</span>
                                  <span className="text-slate-500 font-sans">p.{cit.page_number}</span>
                                  {cit.quoted_span && (
                                    <span className="italic text-slate-400 max-w-[120px] truncate hidden sm:inline">
                                      "{cit.quoted_span}"
                                    </span>
                                  )}
                                  <ExternalLink className="w-2.5 h-2.5 text-indigo-400" />
                                </button>
                              );
                            }

                            // Policy Clause / Chunk Citation
                            return (
                              <div
                                key={cIdx}
                                className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md border border-slate-200 bg-white text-slate-700 shadow-2xs font-mono"
                              >
                                <BookOpen className="w-3 h-3 text-slate-500 shrink-0" />
                                <span>{String(cit.policy_id || cit.section || cit.title || 'Policy Clause')}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input Dock at Bottom of Q&A Panel */}
      <div className="p-3 border-t border-slate-200 bg-slate-50 shrink-0 space-y-2">
        <div className="relative">
          <textarea
            ref={textareaRef}
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSubmitting}
            placeholder="Ask question on policy guidelines, tolerances, or evidence..."
            className="w-full text-xs p-2.5 pr-14 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-white placeholder:text-slate-400 disabled:bg-slate-100 disabled:opacity-60 resize-none shadow-2xs"
          />
          <div className="absolute right-2 bottom-2.5">
            <button
              type="button"
              onClick={() => handleAsk()}
              disabled={!query.trim() || isSubmitting}
              className="inline-flex items-center justify-center p-1.5 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors shadow-2xs"
              title="Ask Question (Enter)"
            >
              {isSubmitting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between text-[10px] text-slate-400 px-0.5">
          <span>Press <strong>Enter</strong> to submit · <strong>Shift+Enter</strong> for newline</span>
          <span className="font-mono">{query.length} chars</span>
        </div>
      </div>
    </div>
  );
};
