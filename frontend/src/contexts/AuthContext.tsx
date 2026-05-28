import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import api from '../lib/api';

interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'analyst';
  org: {
    id: number;
    name: string;
    slug: string;
  } | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await api.get('/auth/me/');
      setUser(response.data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    // Fetch CSRF token first (sets csrftoken cookie)
    await api.get('/auth/csrf/');

    // Then login (api interceptor adds X-CSRFToken header automatically)
    const response = await api.post('/auth/login/', { username, password });
    setUser(response.data.user);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout/');
    } catch (error) {
      console.error('Logout error:', error);
    }
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'admin',
      }}
    >
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
