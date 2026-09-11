import React, { useEffect, useRef, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { UNDERWRITER_PERSONAS } from '../../services/auth';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (opts: { client_id: string; callback: (resp: { credential: string }) => void; auto_select?: boolean; cancel_on_tap_outside?: boolean }) => void;
          renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
          prompt: () => void;
        };
      };
    };
  }
}

function loadGisScript(): Promise<void> {
  if (typeof document === 'undefined') return Promise.resolve();
  if (document.querySelector('script[data-gis="1"]')) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://accounts.google.com/gsi/client';
    s.async = true;
    s.defer = true;
    s.dataset.gis = '1';
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('Failed to load Google Identity Services'));
    document.head.appendChild(s);
  });
}

/**
 * Real loan-app start: explicit sign-in gate.
 * Google mode: GIS button -> POST /auth/google (allowlisted only).
 * Mock mode: 1-click personas for offline/viva.
 */
export const LoginPage: React.FC<{ onLoggedIn?: () => void }> = ({ onLoggedIn }) => {
  const { mode, login, loginWithGoogle, isLoading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const btnRef = useRef<HTMLDivElement | null>(null);
  const clientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string) || '';

  useEffect(() => {
    if (mode !== 'google' || !clientId) return;
    let cancelled = false;
    (async () => {
      try {
        await loadGisScript();
        if (cancelled || !window.google || !btnRef.current) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (resp) => {
            setBusy(true);
            setError(null);
            try {
              await loginWithGoogle(resp.credential);
              onLoggedIn?.();
            } catch (e) {
              setError(e instanceof Error ? e.message : 'Google sign-in failed');
            } finally {
              setBusy(false);
            }
          },
          auto_select: false,
          cancel_on_tap_outside: true,
        });
        btnRef.current.innerHTML = '';
        window.google.accounts.id.renderButton(btnRef.current, {
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'rectangular',
        });
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Google script failed to load');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mode, clientId, loginWithGoogle, onLoggedIn]);

  const handleMock = async (personaId: string) => {
    setBusy(true);
    setError(null);
    try {
      await login(personaId);
      onLoggedIn?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Mock login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen w-screen flex items-center justify-center bg-theme-app px-4">
      <div className="w-full max-w-md bg-theme-card border border-theme-border rounded-xs shadow-md p-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-sm bg-theme-brand flex items-center justify-center text-white">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-serif font-bold text-lg text-theme-primary">FinScan AI</h1>
            <p className="text-[11px] font-mono uppercase tracking-widest text-theme-muted">Institutional Appraisal Desk — Sign in</p>
          </div>
        </div>
        <p className="text-xs text-theme-secondary leading-relaxed mb-5">
          Authorized underwriters only. Customer dossiers never leave the audit trail; every sign-off is attributed.
        </p>

        {mode === 'google' ? (
          <div className="space-y-4">
            {!clientId && (
              <div className="text-xs bg-theme-flag-bg border border-theme-flag-border text-theme-flag rounded-xs p-2.5">
                Missing <code>VITE_GOOGLE_CLIENT_ID</code>. Set it in <code>apps/ui/.env</code> to enable Google sign-in.
              </div>
            )}
            <div ref={btnRef} className="flex justify-center min-h-[44px]" />
            {(isLoading || busy) && <p className="text-xs text-theme-muted text-center">Verifying with server…</p>}
            {error && <div className="text-xs bg-theme-flag-bg border border-theme-flag-border text-theme-flag rounded-xs p-2.5 break-words">{error}</div>}
            <div className="text-[11px] text-theme-muted text-center">
              Only allowlisted Google accounts can sign in. Contact admin with your @work email if denied.
            </div>
          </div>
        ) : (
          <div className="space-y-2.5">
            <p className="text-[11px] font-mono uppercase tracking-widest text-theme-muted">Mock mode — continue as</p>
            {Object.values(UNDERWRITER_PERSONAS).map((p) => (
              <button
                key={p.id}
                type="button"
                disabled={busy}
                onClick={() => handleMock(p.id)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xs bg-theme-panel hover:bg-theme-card border border-theme-border text-left transition-colors disabled:opacity-50"
              >
                {p.avatarUrl ? (
                  <img src={p.avatarUrl} alt={p.name} className="w-8 h-8 rounded-full object-cover" />
                ) : null}
                <span>
                  <span className="block text-xs font-semibold text-theme-primary">{p.name}</span>
                  <span className="block text-[11px] font-mono text-theme-muted">{p.role} • {p.email}</span>
                </span>
              </button>
            ))}
            {error && <div className="text-xs text-theme-flag">{error}</div>}
            <p className="text-[11px] text-theme-muted">Mock JWT for demo only. Set <code>VITE_AUTH_MODE=google</code> + backend <code>AUTH_MODE=google</code> for prod.</p>
          </div>
        )}
      </div>
    </div>
  );
};
