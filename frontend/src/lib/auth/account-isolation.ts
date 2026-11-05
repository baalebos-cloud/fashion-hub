import { queryClient } from "@/lib/query-client";
import { useAuthStore } from "@/store/auth.store";
import { useMessagingStore } from "@/store/messaging.store";

/** Measurement drafts live in localStorage per user; body measurements must not outlive a sign-out. */
export const MEASUREMENT_DRAFT_PREFIX = "seam:measurements:draft:";

function clearMeasurementDrafts(): void {
  try {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(MEASUREMENT_DRAFT_PREFIX)) keys.push(key);
    }
    keys.forEach((key) => localStorage.removeItem(key));
  } catch {
    /* Storage may be blocked; nothing to clear. */
  }
}

/**
 * Wipe everything held in memory for the previous account when the signed-in
 * identity changes or the session ends, so a shared device never shows one
 * person's orders, messages or profile to the next. The AI store resets itself
 * the same way (see store/ai.store.ts).
 */
export function wipeAccountState({ signedOut }: { signedOut: boolean }): void {
  queryClient.cancelQueries();
  queryClient.clear();
  useMessagingStore.getState().reset();
  if (signedOut) clearMeasurementDrafts();
}

useAuthStore.subscribe((state, previous) => {
  const identityChanged = (state.user?.id ?? null) !== (previous.user?.id ?? null);
  const signedOut = previous.isAuthenticated && !state.isAuthenticated;
  if (identityChanged || signedOut) wipeAccountState({ signedOut });
});
