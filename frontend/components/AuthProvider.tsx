/**
 * Authentication context provider.
 * Wraps the entire app to provide auth state and methods.
 */
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { auth0Client, getAccessToken, getUser, isAuthenticated } from '@/lib/auth0';

interface User {
  name?: string;
  email?: string;
  picture?: string;
  sub?: string;
  role?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuth, setIsAuth] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    initializeAuth();
  }, []);

  async function initializeAuth() {
    try {
      // Handle redirect callback if present
      const query = window.location.search;
      if (query.includes('code=') && query.includes('state=')) {
        try {
          await auth0Client.handleRedirectCallback();
        } catch {
          // Stale or duplicate callback — ignore
        }
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }

      // Check authentication status
      const authenticated = await isAuthenticated();
      setIsAuth(authenticated);

      if (authenticated) {
        const userData = await getUser();
        setUser(userData ?? null);

        // Fetch database role in the background (non-blocking)
        getAccessToken().then((token) => {
          if (!token) return;
          const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          fetch(`${API_URL}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          })
            .then((res) => (res.ok ? res.json() : null))
            .then((dbProfile) => {
              if (dbProfile?.role) {
                setUser((prev) => (prev ? { ...prev, role: dbProfile.role } : prev));
              }
            })
            .catch(() => {});
        });
      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
      setIsAuth(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLogin() {
    try {
      await auth0Client.loginWithRedirect();
    } catch (error) {
      console.error('Login failed:', error);
    }
  }

  async function handleLogout() {
    try {
      await auth0Client.logout({
        logoutParams: {
          returnTo: window.location.origin,
        },
      });
      setUser(null);
      setIsAuth(false);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }

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
