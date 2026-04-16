import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { type SubjectResponse, type SubjectType, logout as apiLogout, register as apiRegister, getMe } from '../api/auth';

interface AuthContextType {
  subject: SubjectResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setSubject: (subject: SubjectResponse) => void;
  register: (subjectType: SubjectType, email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [subject, setSubject] = useState<SubjectResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      getMe()
        .then(setSubject)
        .catch(() => {
          clearTokens();
          setSubject(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (subjectType: SubjectType, email: string, password: string, displayName: string) => {
    await apiRegister(subjectType, email, password, displayName);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      clearTokens();
      setSubject(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ subject, isAuthenticated: !!subject, isLoading, setSubject, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
