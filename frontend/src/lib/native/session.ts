/**
 * Keeps the sign-in in the phone's secure storage (iOS Keychain / Android Keystore) so the
 * app stays signed in after it is closed. The website is unchanged: there, tokens live only
 * in sessionStorage (see lib/auth/token.ts).
 *
 * The app copies the stored tokens into sessionStorage before it renders, so the rest of the
 * code reads them the same way on every platform.
 */
import { isNativeApp } from "./platform";

const KEYS = ["tailora.access_token", "tailora.refresh_token"] as const;

// Wrapped in an object on purpose: a Capacitor plugin must never be returned straight from an
// async function, because `await` probes it for `.then`, which the plugin proxy treats as a
// native call that never answers (the app would hang on the launch screen).
async function storage() {
  const { SecureStorage, KeychainAccess } = await import("@aparajita/capacitor-secure-storage");
  // Never synced to iCloud; readable after the phone's first unlock (needed for background calls later).
  await SecureStorage.setDefaultKeychainAccess(KeychainAccess.afterFirstUnlockThisDeviceOnly);
  await SecureStorage.setSynchronize(false);
  return { vault: SecureStorage };
}

/** Run once before the app renders. */
export async function restoreNativeSession(): Promise<void> {
  if (!isNativeApp()) return;
  try {
    const { vault } = await storage();
    for (const key of KEYS) {
      const value = await vault.getItem(key);
      if (value) sessionStorage.setItem(key, value);
    }
  } catch {
    // Unreadable storage just means signing in again.
  }
}

export function persistNativeSession(tokens: { accessToken: string; refreshToken: string } | null): void {
  if (!isNativeApp()) return;
  void (async () => {
    try {
      const { vault } = await storage();
      if (tokens) {
        await vault.setItem(KEYS[0], tokens.accessToken);
        await vault.setItem(KEYS[1], tokens.refreshToken);
      } else {
        for (const key of KEYS) await vault.removeItem(key);
      }
    } catch {
      // Best effort: the session still works until the app is closed.
    }
  })();
}
