import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiService } from '@/services/api';
import { clearAuthTokens, getAccessToken, getRefreshToken, saveAuthTokens } from '@/lib/authStorage';

export type UserRole = 'admin' | 'user';

interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string, role: UserRole) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      const token = getAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const me = await apiService.getCurrentUser(token);
        const roles = Array.isArray(me?.roles) ? me.roles : [];
        const email = typeof me?.subject === 'string' ? me.subject : 'user';
        const normalizedUser: User = {
          id: email,
          email,
          name: email.split('@')[0] || email,
          role: roles.includes('admin') ? 'admin' : 'user',
        };
        setUser(normalizedUser);
      } catch {
        clearAuthTokens();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    void restoreSession();
  }, []);

  const login = async (email: string, password: string, _role: UserRole) => {
    const payload = await apiService.login(email, password);
    const accessToken = String(payload?.access_token || '');
    const refreshToken = String(payload?.refresh_token || '');
    if (!accessToken) {
      throw new Error('Missing access token from login response');
    }

    saveAuthTokens(accessToken, refreshToken || undefined);

    const me = await apiService.getCurrentUser(accessToken);
    const roles = Array.isArray(me?.roles) ? me.roles : [];
    const subject = typeof me?.subject === 'string' && me.subject ? me.subject : email;
    const normalizedUser: User = {
      id: subject,
      email,
      name: subject.split('@')[0] || subject,
      role: roles.includes('admin') ? 'admin' : 'user',
    };
    setUser(normalizedUser);
  };

  const logout = () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      void apiService.logout(refreshToken).catch(() => undefined);
    }
    clearAuthTokens();
    setUser(null);
  };

  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
