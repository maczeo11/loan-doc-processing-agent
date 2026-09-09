import React, { createContext, useContext, useState, useEffect } from 'react';
import { AuthContextType, UnderwriterProfile, UnderwriterRole } from '../types/auth';
import { AuthService, UNDERWRITER_PERSONAS } from '../services/auth';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UnderwriterProfile | null>(() => AuthService.getStoredUser());
  const [mode] = useState<'google' | 'mock'>(
    (import.meta.env.VITE_AUTH_MODE as 'google' | 'mock') || 'mock'
  );

  useEffect(() => {
    if (!user) {
      const defaultUser = AuthService.getStoredUser();
      if (defaultUser) {
        setUser(defaultUser);
      }
    }
  }, [user]);

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
    AuthService.clearUser();
    setUser(null);
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
        logout,
        isAuthenticated: !!user,
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
