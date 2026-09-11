import { UnderwriterProfile, UnderwriterRole } from '../types/auth';

const STORAGE_KEY = 'finscan_underwriter_session';

export const UNDERWRITER_PERSONAS: Record<UnderwriterRole, UnderwriterProfile> = {
  SENIOR_UNDERWRITER: {
    id: 'USR-AKSHAYA-01',
    name: 'Akshaya S.',
    email: 'akshaya.underwriting@finscan.internal',
    role: 'SENIOR_UNDERWRITER',
    token: 'mock_jwt_token_senior_underwriter_akshaya_2026',
    avatarUrl: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=100&auto=format&fit=crop&q=80',
  },
  RISK_ANALYST: {
    id: 'USR-KARTHIK-02',
    name: 'Karthik R.',
    email: 'karthik.risk@finscan.internal',
    role: 'RISK_ANALYST',
    token: 'mock_jwt_token_risk_analyst_karthik_2026',
    avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80',
  },
  COMPLIANCE_OFFICER: {
    id: 'USR-MANJU-03',
    name: 'Manjunath V.',
    email: 'manju.compliance@finscan.internal',
    role: 'COMPLIANCE_OFFICER',
    token: 'mock_jwt_token_compliance_officer_manju_2026',
    avatarUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80',
  },
};

export class AuthService {
  static getStoredUser(): UnderwriterProfile | null {
    try {
      const data = sessionStorage.getItem(STORAGE_KEY);
      if (data) {
        return JSON.parse(data) as UnderwriterProfile;
      }
    } catch {
      // Ignore sessionStorage parsing errors
    }
    // Google mode: no auto-login (real loan-app start requires explicit sign-in).
    // Mock mode: seamless demo fallback preserves viva/offline flow.
    try {
      const mode = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_AUTH_MODE;
      if (mode === 'google') return null;
    } catch {
      /* ignore */
    }
    return UNDERWRITER_PERSONAS.SENIOR_UNDERWRITER;
  }

  /** Session JWT (memory + sessionStorage; httpOnly cookie is primary server-side). */
  static getSessionToken(): string | null {
    try {
      return sessionStorage.getItem('finscan_session_jwt');
    } catch {
      return null;
    }
  }

  static storeSessionToken(token: string): void {
    try {
      sessionStorage.setItem('finscan_session_jwt', token);
    } catch {
      /* ignore */
    }
  }

  /** POST /auth/google {id_token} -> {user, session_jwt}. Throws with status on 403/401. */
  static async exchangeGoogleIdToken(idToken: string): Promise<UnderwriterProfile> {
    const res = await fetch('/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ id_token: idToken }),
    });
    if (!res.ok) {
      const detail = (await res.text()).slice(0, 200);
      const err = new Error(res.status === 403 ? `Access restricted — ${detail || 'account not allowlisted'}` : `Google sign-in failed (${res.status}): ${detail}`);
      (err as unknown as { status: number }).status = res.status;
      throw err;
    }
    const data = await res.json();
    if (data.session_jwt) AuthService.storeSessionToken(data.session_jwt);
    const profile: UnderwriterProfile = {
      id: data.user?.email || 'google-user',
      name: data.user?.name || 'Underwriter',
      email: data.user?.email || '',
      role: (data.user?.role as UnderwriterRole) || 'SENIOR_UNDERWRITER',
      token: data.session_jwt || 'google-session',
      avatarUrl: data.user?.picture_url,
    };
    AuthService.storeUser(profile);
    return profile;
  }

  static async fetchMe(): Promise<UnderwriterProfile | null> {
    try {
      const headers: Record<string, string> = {};
      const tok = AuthService.getSessionToken();
      if (tok) headers.Authorization = `Bearer ${tok}`;
      const res = await fetch('/auth/me', { headers, credentials: 'include' });
      if (!res.ok) return null;
      const data = await res.json();
      const profile: UnderwriterProfile = {
        id: data.email, name: data.name || 'Underwriter', email: data.email,
        role: (data.role as UnderwriterRole) || 'SENIOR_UNDERWRITER',
        token: tok || 'google-session', avatarUrl: data.picture_url,
      };
      AuthService.storeUser(profile);
      return profile;
    } catch {
      return null;
    }
  }

  static async serverLogout(): Promise<void> {
    try {
      await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
    } catch {
      /* ignore */
    }
    try {
      sessionStorage.removeItem('finscan_session_jwt');
    } catch {
      /* ignore */
    }
    AuthService.clearUser();
  }

  static storeUser(user: UnderwriterProfile): void {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } catch {
      // Ignore sessionStorage write errors
    }
  }

  static clearUser(): void {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore
    }
  }

  static getAvailablePersonas(): UnderwriterProfile[] {
    return Object.values(UNDERWRITER_PERSONAS);
  }

  static getPersonaByRole(role: UnderwriterRole): UnderwriterProfile {
    return UNDERWRITER_PERSONAS[role];
  }
}
