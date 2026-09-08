/**
 * ProtectedRoute — route guard theo auth + RBAC.
 * Tiêu chí 7: routing tách khỏi component.
 * Tiêu chí 8: permission check tập trung.
 */
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { LoadingOverlay } from '@components/ui';
import { ROUTES } from '@/app/routes';

interface ProtectedRouteProps {
  /** Nếu truyền, kiểm tra user có permission này không */
  permission?: string;
}

export function ProtectedRoute({ permission }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, can } = useAuth();
  const location = useLocation();

  if (isLoading) return <LoadingOverlay />;

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  if (permission && !can(permission)) {
    return <Navigate to={ROUTES.FORBIDDEN} replace />;
  }

  return <Outlet />;
}
