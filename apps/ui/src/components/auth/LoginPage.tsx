import React, { useState } from 'react';
import { ShieldCheck } from 'lucide-react';

/** Official Google "G" mark, inline so no extra asset/network fetch is needed. */
const GoogleIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 18 18" aria-hidden="true">
    <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.68-3.87 2.68-6.62z" />
    <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.83.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.96v2.33A9 9 0 0 0 9 18z" />
    <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.97H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.03l2.99-2.33z" />
    <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.97l2.99 2.33C4.66 5.17 6.65 3.58 9 3.58z" />
  </svg>
);
import {
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
} from 'firebase/auth';
import { auth, googleProvider } from '../../lib/firebase';
import { useAuth } from '../../context/AuthContext';
import { UNDERWRITER_PERSONAS, initialsFor } from '../../services/auth';

/**
 * Real loan-app start: explicit sign-in gate.
 * Firebase mode: Google popup or email/password, both via Firebase Auth ->
 * exchange the resulting Firebase ID token with the backend (allowlisted only).
 * Mock mode: 1-click personas for offline/viva.
 */
export const LoginPage: React.FC<{ onLoggedIn?: () => void }> = ({ onLoggedIn }) => {
  const { mode, login, loginWithGoogle, isLoading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);

  const finishWithFirebaseUser = async (getIdToken: () => Promise<string>) => {
    setBusy(true);
    setError(null);
    try {
      const idToken = await getIdToken();
      await loginWithGoogle(idToken);
      onLoggedIn?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Sign-in failed');
    } finally {
      setBusy(false);
    }
  };

  const handleGooglePopup = () =>
    finishWithFirebaseUser(async () => {
      const result = await signInWithPopup(auth, googleProvider);
      return result.user.getIdToken();
    });

  const handleEmailPassword = (e: React.FormEvent) => {
    e.preventDefault();
    finishWithFirebaseUser(async () => {
      const result = isSignUp
        ? await createUserWithEmailAndPassword(auth, email, password)
        : await signInWithEmailAndPassword(auth, email, password);
      return result.user.getIdToken();
    });
  };

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
            <button
              type="button"
              disabled={busy || isLoading}
              onClick={handleGooglePopup}
              className="w-full flex items-center justify-center gap-2.5 px-3 py-2.5 rounded-xs border border-theme-border bg-white hover:bg-theme-panel transition-colors disabled:opacity-50 text-xs font-semibold text-gray-700 shadow-2xs"
            >
              <GoogleIcon />
              Sign in with Google
            </button>

            <div className="flex items-center gap-2 text-[10px] text-theme-muted uppercase tracking-wider">
              <div className="flex-1 h-px bg-theme-border" />
              or
              <div className="flex-1 h-px bg-theme-border" />
            </div>

            <form onSubmit={handleEmailPassword} className="space-y-2.5">
              <input
                type="email"
                required
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xs bg-theme-panel border border-theme-border text-theme-primary placeholder:text-theme-muted focus:outline-none focus:border-theme-brand"
              />
              <input
                type="password"
                required
                minLength={6}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xs bg-theme-panel border border-theme-border text-theme-primary placeholder:text-theme-muted focus:outline-none focus:border-theme-brand"
              />
              <button
                type="submit"
                disabled={busy || isLoading}
                className="w-full px-3 py-2.5 rounded-xs bg-theme-brand text-white text-xs font-semibold disabled:opacity-50"
              >
                {isSignUp ? 'Create account' : 'Sign in'}
              </button>
              <button
                type="button"
                onClick={() => setIsSignUp((v) => !v)}
                className="w-full text-[11px] text-theme-muted hover:text-theme-primary text-center"
              >
                {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Create one"}
              </button>
            </form>

            {(isLoading || busy) && <p className="text-xs text-theme-muted text-center">Verifying with server…</p>}
            {error && <div className="text-xs bg-theme-flag-bg border border-theme-flag-border text-theme-flag rounded-xs p-2.5 break-words">{error}</div>}
            <div className="text-[11px] text-theme-muted text-center">
              Only allowlisted accounts can sign in. Contact admin with your @work email if denied.
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
                <span className="w-8 h-8 rounded-full bg-theme-brand/10 border border-theme-border flex items-center justify-center text-[11px] font-mono font-bold text-theme-brand shrink-0">
                  {initialsFor(p.name)}
                </span>
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
