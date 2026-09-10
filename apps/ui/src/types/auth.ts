export type UnderwriterRole = 'SENIOR_UNDERWRITER' | 'RISK_ANALYST' | 'COMPLIANCE_OFFICER';

export interface UnderwriterProfile {
  id: string;
  name: string;
  email: string;
  role: UnderwriterRole;
  avatarUrl?: string;
  token: string;
}

export interface AuthContextType {
  user: UnderwriterProfile | null;
  mode: 'google' | 'mock';
  login: (personaId?: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  switchPersona: (role: UnderwriterRole) => void;
}
