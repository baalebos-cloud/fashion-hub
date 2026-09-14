import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { authRoutes } from "@/config/routes.config";
import { Spinner } from "@/components/ui/spinner";

/**
 * Blocks unauthenticated access to every /app/* route. This is a UX
 * convenience — it stops an obviously-unauthenticated browser from
 * flashing protected UI before redirecting. It is NOT the security
 * boundary: every API call the resulting pages make is independently
 * authorized by the backend regardless of what this guard decided (see
 * backend/docs/security.md). Never reason "the route is guarded, so this
 * data must be safe to show."
 */
export function AuthGuard() {
  const { isAuthenticated, isInitializing } = useAuth();
  const location = useLocation();

  if (isInitializing) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={authRoutes.login} state={{ from: location }} replace />;
  }

  return <Outlet />;
}
