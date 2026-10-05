/**
 * Authentication context provider.
 * Wraps the entire app to provide auth state and methods.
 */
'use client';

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { getUser, isAuthenticated, handleRedirectCallback, login as auth0Login, logout as auth0Logout } from '@/lib/auth0';

interface User {
  name?: string;
  email?: string;
  picture?: string;
  sub?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (returnTo?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuth, setIsAuth] = useState(false);
  const [isLoading, setIsLoading] = useState(process.env.NEXT_PUBLIC_APP_TARGET !== 'toss');

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_APP_TARGET !== 'toss') initializeAuth();
  }, []);

  async function initializeAuth() {
    try {
      // Handle redirect callback if present
      const query = window.location.search;
      if (query.includes('code=') && query.includes('state=')) {
        const returnTo = await handleRedirectCallback();
        if (returnTo !== window.location.pathname) {
          window.location.replace(returnTo);
          return;
        }
        window.history.replaceState({}, document.title, returnTo);
      }

      // Check authentication status
      const authenticated = await isAuthenticated();
      setIsAuth(authenticated);

      if (authenticated) {
        const userData = await getUser();
        setUser(userData ?? null);

      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
      setIsAuth(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }

  const handleLogin = useCallback(async (returnTo = '/') => {
    try {
      await auth0Login(returnTo);
    } catch (error) {
      console.error('Login failed:', error);
    }
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await auth0Logout();
      setUser(null);
      setIsAuth(false);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: isAuth,
        isLoading,
        login: handleLogin,
        logout: handleLogout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to access auth context.
 * Must be used within AuthProvider.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
