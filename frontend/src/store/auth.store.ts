import { create } from "zustand";
import { authApi } from "@/api/auth.api";
import { restoreSession } from "@/lib/auth/session";
import { clearTokens, getRefreshToken, setTokens } from "@/lib/auth/token";
import type { User } from "@/types/user";
import type { LogInPayload, SignUpPayload } from "@/types/auth";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  error: string | null;

  initialize: () => Promise<void>;
  logIn: (payload: LogInPayload) => Promise<void>;
  signUp: (payload: SignUpPayload) => Promise<void>;
  logOut: () => Promise<void>;
}

/**
 * The single source of truth for "who is logged in," consumed by
 * hooks/use-auth.ts (the only file most components should import from —
 * see that file for why). `initialize()` runs once at app boot to turn a
 * persisted token into a hydrated `user` object before the router renders
 * any protected route.
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isInitializing: true,
  error: null,

  initialize: async () => {
    const user = await restoreSession();
    set({ user, isAuthenticated: user !== null, isInitializing: false });
  },

  logIn: async (payload) => {
    set({ error: null });
    try {
      const tokens = await authApi.logIn(payload);
      setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      const user = await restoreSession();
      set({ user, isAuthenticated: user !== null });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Login failed." });
      throw err;
    }
  },

  signUp: async (payload) => {
    set({ error: null });
    try {
      await authApi.signUp(payload);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Sign up failed." });
      throw err;
    }
  },

  logOut: async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await authApi.logOut(refreshToken);
      } catch {
        // Best-effort server-side revocation; clear the local session
        // regardless so the person is signed out on this device either way.
      }
    }
    clearTokens();
    set({ user: null, isAuthenticated: false });
  },
}));
