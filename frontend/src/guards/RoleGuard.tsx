import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { ROLE_HOME_PATH } from "@/constants/roles";
import type { UserRole } from "@/types/auth";

/**
 * Generic role gate — the specific *Guard components below (CustomerGuard,
 * ProfessionalGuard, etc.) are just this with a fixed role list, kept as
 * separate files because router/*.routes.tsx reads more clearly wrapping
 * routes in `<CustomerGuard>` than `<RoleGuard roles={["customer"]}>`
 * repeated at every call site.
 *
 * Same caveat as AuthGuard: this decides what renders, not what's
 * authorized. A customer navigating to /app/vendor gets redirected home
 * here, but even if they somehow reached a vendor page, every API call it
 * makes would still be rejected server-side.
 */
export function RoleGuard({ allowedRoles }: { allowedRoles: UserRole[] }) {
  const { user } = useAuth();

  if (!user) return null; // AuthGuard (which always wraps this) already handles the unauthenticated case

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={ROLE_HOME_PATH[user.role]} replace />;
  }

  return <Outlet />;
}
