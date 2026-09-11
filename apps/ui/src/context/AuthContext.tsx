import React, { createContext, useContext, useState, useEffect } from 'react';
import { AuthContextType, UnderwriterProfile, UnderwriterRole } from '../types/auth';
import { AuthService, UNDERWRITER_PERSONAS } from '../services/auth';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UnderwriterProfile | null>(() => AuthService.getStoredUser());
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [mode] = useState<'google' | 'mock'>(
    (import.meta.env.VITE_AUTH_MODE as 'google' | 'mock') || 'mock'
  );

  useEffect(() => {
    // Google mode: try server session once on boot (httpOnly cookie + /auth/me).
    if (mode === 'google' && !user) {
      setIsLoading(true);
      AuthService.fetchMe()
        .then((me) => {
          if (me) setUser(me);
        })
        .finally(() => setIsLoading(false));
    }
  }, [mode]);

  const login = async (personaId?: string): Promise<void> => {
    if (personaId) {
      const found = Object.values(UNDERWRITER_PERSONAS).find((p) => p.id === personaId);
      if (found) {
        AuthService.storeUser(found);
        setUser(found);
        return;
      }
    }
    const defaultSenior = UNDERWRITER_PERSONAS.SENIOR_UNDERWRITER;
    AuthService.storeUser(defaultSenior);
    setUser(defaultSenior);
  };

  const logout = () => {
    AuthService.serverLogout().finally(() => setUser(null));
    // In mock mode restore seamless demo user after sign-out? No — stay signed out
    // so LoginPage/Dashboard gating is visible. Mock LoginPage offers 1-click personas.
  };

  const loginWithGoogle = async (idToken: string): Promise<void> => {
    setIsLoading(true);
    try {
      const profile = await AuthService.exchangeGoogleIdToken(idToken);
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshMe = async (): Promise<void> => {
    const me = await AuthService.fetchMe();
    if (me) setUser(me);
  };

  const switchPersona = (role: UnderwriterRole) => {
    const profile = AuthService.getPersonaByRole(role);
    AuthService.storeUser(profile);
    setUser(profile);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        mode,
        login,
        loginWithGoogle,
        refreshMe,
        logout,
        isAuthenticated: !!user,
        isLoading,
        switchPersona,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
