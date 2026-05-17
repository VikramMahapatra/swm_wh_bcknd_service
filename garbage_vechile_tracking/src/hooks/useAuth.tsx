import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

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
    // Check for existing session - but don't auto-login
    // User must explicitly login each time for security
    const savedUser = localStorage.getItem('mockUser');
    if (savedUser) {
      try {
        const parsed = JSON.parse(savedUser);
        // Validate session is still valid (optional: add expiry check)
        if (parsed && parsed.id && parsed.email && parsed.role) {
          setUser(parsed);
        } else {
          localStorage.removeItem('mockUser');
        }
      } catch {
        localStorage.removeItem('mockUser');
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string, role: UserRole) => {
    // Mock login - in production this would call your backend with proper authentication
    const mockUser: User = {
      id: role === 'admin' ? 'admin-1' : 'user-1',
      email,
      name: email.split('@')[0],
      role,
    };
    
    localStorage.setItem('mockUser', JSON.stringify(mockUser));
    setUser(mockUser);
  };

  const logout = () => {
    localStorage.removeItem('mockUser');
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
