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
    // Default fallback to Senior Underwriter for seamless demo
    return UNDERWRITER_PERSONAS.SENIOR_UNDERWRITER;
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
