import { usersApi } from "@/api/users.api";
import { hasSession, clearTokens } from "./token";
import type { User } from "@/types/user";

/**
 * Called once, on app boot (see store/auth.store.ts), to turn "a token
 * exists in storage" into "we know who this user is." Kept separate from
 * the store itself so it's easy to unit test without pulling in Zustand.
 */
export async function restoreSession(): Promise<User | null> {
  if (!hasSession()) return null;

  try {
    return await usersApi.getCurrentUser();
  } catch {
    // Token exists but is invalid/expired and refresh already failed
    // (the interceptor would have retried once) — clear it so the app
    // doesn't keep treating this as a logged-in state.
    clearTokens();
    return null;
  }
}
