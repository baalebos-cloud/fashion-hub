import { Navigate } from "react-router-dom";
import { ROLE_HOME_PATH } from "@/constants/roles";
import { useAuth } from "@/hooks/use-auth";

/**
 * "/app" on its own: the signed-in person's dashboard. Signed-out visitors are sent to sign in by
 * AuthGuard first, then come back here and land on their dashboard.
 */
export function AppHome() {
  const { user } = useAuth();
  return <Navigate to={user ? ROLE_HOME_PATH[user.role] : "/login"} replace />;
}
