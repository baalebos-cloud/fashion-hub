/** Same contract as local-storage.ts, backed by sessionStorage, for
 * transient per-tab UI state (e.g. "has the welcome tour been dismissed
 * this session"). Not for auth tokens — see lib/auth/token.ts, which owns
 * that specific storage key naming and lifecycle directly. */
export function getSessionItem<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function setSessionItem<T>(key: string, value: T): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore
  }
}
