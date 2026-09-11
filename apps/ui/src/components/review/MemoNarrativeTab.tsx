import React, { useState } from 'react';
import { LoanApplication } from '../../types/application';
import { sanitizePiiInText } from '../../utils/pii';
import { api, downloadBlobUrl } from '../../services/api';
import { Download, FileText, ShieldCheck, ShieldAlert, Loader2, AlertTriangle } from 'lucide-react';

interface MemoNarrativeTabProps {
  application: LoanApplication;
  /** Preset archetypes have no backend dossier to export. */
  isReadOnlyPreset?: boolean;
}

/**
 * Minimal, dependency-free Markdown rendering for the memo.
 *
 * The memo arrives as Markdown; rendering it in a `whitespace-pre-wrap` block
 * showed readers literal `##` and `**` markers. This covers exactly what the
 * memo builder emits — headings, bullets, bold — and nothing else.
 */
function renderMarkdown(markdown: string): React.ReactNode[] {
  const withBold = (text: string): React.ReactNode[] =>
    text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={i} className="font-bold text-theme-primary">
          {part.slice(2, -2)}
        </strong>
      ) : (
        <React.Fragment key={i}>{part}</React.Fragment>
      )
    );

  return markdown.split('\n').map((rawLine, idx) => {
    const line = rawLine.trimEnd();
    if (!line.trim()) return <div key={idx} className="h-2" />;

    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      const sizes = ['text-base', 'text-sm', 'text-[13px]', 'text-xs'];
      return (
        <h3
          key={idx}
          className={`${sizes[level - 1]} font-serif font-bold text-theme-primary mt-3 mb-1 first:mt-0`}
        >
          {withBold(heading[2])}
        </h3>
      );
    }

    const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
    if (bullet) {
      return (
        <div key={idx} className="flex gap-2 pl-1">
          <span className="text-theme-muted select-none">•</span>
          <span className="flex-1">{withBold(bullet[1])}</span>
        </div>
      );
    }

    if (/^\s*([-=_])\1{2,}\s*$/.test(line)) {
      return <hr key={idx} className="my-2 border-theme-border" />;
    }

    return <p key={idx}>{withBold(line)}</p>;
  });
}

export const MemoNarrativeTab: React.FC<MemoNarrativeTabProps> = ({
  application,
  isReadOnlyPreset = false,
}) => {
  const hasMemo = !!application.memo_markdown?.trim();
  const narrative = application.memo_markdown || 'Credit Appraisal Memo generation pending.';
  const grounded = !!application.summary_grounded;
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExportMarkdown = () => {
    const blob = new Blob([sanitizePiiInText(narrative)], { type: 'text/markdown;charset=utf-8;' });
    downloadBlobUrl(URL.createObjectURL(blob), `CAM_${application.id}.md`);
  };

  // Goes through the authenticated client so the session travels with it and a
  // 409/501 renders inline instead of opening a raw JSON error page in a tab.
  const handleExportPdf = async () => {
    setExporting(true);
    setExportError(null);
    try {
      const result = await api.exportApplication(application.id, 'pdf');
      if ('blobUrl' in result) {
        downloadBlobUrl(result.blobUrl, result.filename);
      } else {
        setExportError('Server did not return a PDF.');
      }
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'PDF export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-3.5">
      {/* Export Header */}
      <div className="flex items-center justify-between gap-2 p-2.5 rounded-xs bg-theme-panel border border-theme-border shadow-xs">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-theme-primary shrink-0" />
          <span className="text-xs font-serif font-bold text-theme-primary truncate">
            Credit Appraisal Memo (CAM)
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleExportPdf}
            disabled={exporting || isReadOnlyPreset || !hasMemo}
            title={
              isReadOnlyPreset
                ? 'Offline preset — no backend dossier to export'
                : !hasMemo
                  ? 'Run the verification pipeline to generate the memo'
                  : 'Download the official CAM PDF'
            }
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-xs bg-theme-panel hover:bg-theme-card text-theme-primary border border-theme-border text-xs font-serif font-semibold transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {exporting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Download className="w-3.5 h-3.5 text-theme-unknown" />
            )}
            <span>PDF CAM</span>
          </button>
          <button
            type="button"
            onClick={handleExportMarkdown}
            disabled={!hasMemo}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-xs bg-theme-card hover:bg-theme-panel text-theme-primary border border-theme-border text-xs font-serif font-semibold transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            title="Export Markdown Memo"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Markdown</span>
          </button>
        </div>
      </div>

      {exportError && (
        <div className="p-2.5 rounded-xs bg-theme-flag-bg border border-theme-flag-border text-theme-flag text-[11px] font-mono flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-px" />
          <span className="break-words">{exportError}</span>
        </div>
      )}

      {/* Memo Content Card - Editorial Paper Aesthetic */}
      <div className="p-5 rounded-xs bg-theme-card border border-theme-border text-xs leading-relaxed text-theme-secondary space-y-3 shadow-xs">
        {/* Grounding state is read from the pipeline, not asserted. A static
            "Zero Hallucinations" badge claimed verification the backend had not
            reported — including over the "generation pending" placeholder. */}
        <div
          className={`flex items-center gap-2 pb-2 border-b border-theme-border text-[10px] font-mono font-medium ${
            grounded ? 'text-theme-pass' : 'text-theme-unknown'
          }`}
        >
          {grounded ? (
            <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
          ) : (
            <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
          )}
          <span>
            {!hasMemo
              ? 'No memo synthesized yet — run the verification pipeline'
              : grounded
                ? 'Grounding verified — every figure traced to cited evidence'
                : 'Not grounding-verified — treat figures as unconfirmed'}
          </span>
        </div>

        <div className="max-w-none font-serif text-theme-primary leading-relaxed text-[13px]">
          {hasMemo ? (
            renderMarkdown(sanitizePiiInText(narrative))
          ) : (
            <p className="text-theme-muted font-sans text-xs">{narrative}</p>
          )}
        </div>
      </div>
    </div>
  );
};
