import { useAuthStore } from "@/store/auth.store";

/**
 * The ONLY way most components should touch auth state — wraps
 * useAuthStore so if the underlying state library ever changes, call
 * sites don't. Also the natural place to add derived/computed auth values
 * later without touching every consumer.
 */
export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isInitializing = useAuthStore((s) => s.isInitializing);
  const error = useAuthStore((s) => s.error);
  const logIn = useAuthStore((s) => s.logIn);
  const signUp = useAuthStore((s) => s.signUp);
  const logOut = useAuthStore((s) => s.logOut);

  return { user, isAuthenticated, isInitializing, error, logIn, signUp, logOut };
}
