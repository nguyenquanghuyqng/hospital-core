/**
 * AuthContext — tập trung toàn bộ auth state.
 * Tiêu chí 4: auth tách khỏi business logic.
 * Tiêu chí 8: RBAC permissions định nghĩa tại đây.
 */
import {
  createContext, useContext, useEffect, useRef,
  useState, useCallback, type ReactNode,
} from 'react';
import { authApi }      from '@api/auth.api';
import { tokenStorage } from '@api/client';
import type { User, UserRole } from '@/types';

// ── Permissions (RBAC) ────────────────────────────────────────────────────────
/** Tiêu chí 8: permission map rõ ràng, tập trung */
export const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  admin:  ['reception', 'queue', 'doctor', 'examination', 'admin'],
  doctor: ['doctor', 'examination'],
  nurse:  ['reception', 'queue'],
};

export function hasPermission(role: UserRole | undefined, permission: string): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

// ── Context shape ─────────────────────────────────────────────────────────────
interface AuthContextValue {
  user:        User | null;
  isLoading:   boolean;
  isAuthenticated: boolean;
  login:  (username: string, password: string) => Promise<void>;
  logout: () => void;
  can:    (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,      setUser]      = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const didInit = useRef(false);

  const logout = useCallback(() => {
    tokenStorage.remove();
    setUser(null);
  }, []);

  // Restore session on mount
  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;

    const token = tokenStorage.get();
    if (!token) { setIsLoading(false); return; }

    authApi.me()
      .then(setUser)
      .catch(() => tokenStorage.remove())
      .finally(() => setIsLoading(false));
  }, []);

  // Listen for 401 from API client
  useEffect(() => {
    const handler = () => logout();
    window.addEventListener('auth:unauthorized', handler);
    return () => window.removeEventListener('auth:unauthorized', handler);
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const token = await authApi.login({ username, password });
    tokenStorage.set(token.access_token);
    const me = await authApi.me();
    setUser(me);
  }, []);

  const can = useCallback(
    (permission: string) => hasPermission(user?.role, permission),
    [user],
  );

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
