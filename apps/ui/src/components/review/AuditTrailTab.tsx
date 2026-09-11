import React, { useCallback, useEffect, useState } from 'react';
import { History, Loader2, AlertTriangle, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import type { AuditEvent } from '../../types/contracts';

interface AuditTrailTabProps {
  applicationId: string;
  /** Offline archetypes have no server-side audit trail. */
  isReadOnlyPreset?: boolean;
}

const DECISION_ACCENT: Record<string, string> = {
  APPROVED: 'bg-theme-pass-bg border-theme-pass-border text-theme-pass',
  REJECTED: 'bg-theme-flag-bg border-theme-flag-border text-theme-flag',
  NEEDS_INFO: 'bg-theme-unknown-bg border-theme-unknown-border text-theme-unknown',
  CANCELLED: 'bg-theme-panel border-theme-border text-theme-secondary',
};

/**
 * Reads the append-only audit trail the sign-off modal promises.
 *
 * Every review and cancellation writes an AuditEventModel row, but there was no
 * route and no view for them: the underwriter who is accountable for a decision
 * could not see what had been recorded against the dossier.
 */
export const AuditTrailTab: React.FC<AuditTrailTabProps> = ({
  applicationId,
  isReadOnlyPreset = false,
}) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (isReadOnlyPreset) return;
    setLoading(true);
    setError(null);
    try {
      setEvents(await api.getAuditTrail(applicationId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit trail');
    } finally {
      setLoading(false);
    }
  }, [applicationId, isReadOnlyPreset]);

  useEffect(() => {
    load();
  }, [load]);

  if (isReadOnlyPreset) {
    return (
      <div className="p-6 text-center border border-dashed border-theme-border rounded-xs bg-theme-panel/30">
        <History className="w-8 h-8 text-theme-muted mx-auto mb-2 opacity-50" />
        <p className="text-xs font-serif font-bold text-theme-primary mb-1">Offline Preset</p>
        <p className="text-[11px] text-theme-muted leading-relaxed">
          Audit events are recorded server-side. Open a live dossier to read its trail.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-theme-border">
        <span className="text-xs font-serif font-bold text-theme-primary">
          Immutable Audit Trail ({events.length})
        </span>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1 text-[10px] font-mono text-theme-muted hover:text-theme-primary px-1.5 py-0.5 rounded-xs border border-theme-border disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="p-2.5 rounded-xs bg-theme-flag-bg border border-theme-flag-border text-theme-flag text-[11px] font-mono flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-px" />
          <span className="break-words">{error}</span>
        </div>
      )}

      {loading && events.length === 0 && (
        <div className="flex items-center gap-2 text-[11px] font-mono text-theme-muted p-4">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Loading audit trail…</span>
        </div>
      )}

      {!loading && !error && events.length === 0 && (
        <div className="p-6 text-center border border-dashed border-theme-border rounded-xs bg-theme-panel/30">
          <History className="w-8 h-8 text-theme-muted mx-auto mb-2 opacity-50" />
          <p className="text-xs font-serif font-bold text-theme-primary mb-1">No Audit Events Yet</p>
          <p className="text-[11px] text-theme-muted leading-relaxed">
            A row is appended here the moment a decision or cancellation is recorded.
          </p>
        </div>
      )}

      <ol className="space-y-2">
        {events.map((event) => (
          <li
            key={event.id}
            className="p-3 rounded-xs bg-theme-card border border-theme-border shadow-2xs space-y-1.5"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-mono font-bold text-theme-primary">
                {event.from_status} → {event.to_status}
              </span>
              {event.decision && (
                <span
                  className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-xs border shrink-0 ${
                    DECISION_ACCENT[event.decision] || 'bg-theme-panel border-theme-border text-theme-secondary'
                  }`}
                >
                  {event.decision}
                </span>
              )}
            </div>
            <div className="text-[10px] font-mono text-theme-muted flex flex-wrap gap-x-2">
              <span className="break-all">{event.actor}</span>
              {event.timestamp && <span>· {new Date(event.timestamp).toLocaleString()}</span>}
            </div>
            {event.notes && (
              <p className="text-[11px] text-theme-secondary leading-relaxed border-t border-theme-border pt-1.5">
                {event.notes}
              </p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
};
