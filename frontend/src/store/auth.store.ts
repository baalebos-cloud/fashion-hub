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
  logIn: (payload: LogInPayload) => Promise<User>;
  signUp: (payload: SignUpPayload) => Promise<void>;
  logOut: () => Promise<void>;
  /** Finish the admin two-step sign-in with the tokens it returned. */
  completeSignIn: (tokens: { access_token: string; refresh_token: string }) => Promise<User>;
  /** Re-read the signed-in user after a profile change (photo, name). */
  refreshUser: () => Promise<void>;
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
      if (!user) throw new Error("Could not restore your session. Please try signing in again.");
      set({ user, isAuthenticated: true });
      return user;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Login failed." });
      throw err;
    }
  },

  completeSignIn: async (tokens) => {
    setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
    const user = await restoreSession();
    if (!user) throw new Error("Could not restore your session. Please try signing in again.");
    set({ user, isAuthenticated: true, error: null });
    return user;
  },

  refreshUser: async () => {
    const user = await restoreSession();
    if (user) set({ user });
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
    // Hang up any call first, while the session can still tell the server.
    try {
      const { useCallStore } = await import("@/store/call.store");
      await useCallStore.getState().reset();
    } catch {
      // Never let call cleanup block signing out.
    }
    try {
      const { unregisterPush } = await import("@/lib/native/push");
      await unregisterPush();
    } catch {
      // The phone simply keeps no push registration for anyone.
    }
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
