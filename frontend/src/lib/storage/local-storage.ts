/** Typed, JSON-safe wrapper over localStorage for non-sensitive UI
 * preferences only (e.g. "sidebar collapsed"). Auth tokens are NEVER
 * stored here — see lib/auth/token.ts, which uses sessionStorage
 * deliberately for a smaller XSS blast radius. */
export function getLocalItem<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function setLocalItem<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage full or disabled (e.g. private browsing) — fail silently;
    // this is only ever used for non-critical UI preferences.
  }
}

export function removeLocalItem(key: string): void {
  localStorage.removeItem(key);
}
