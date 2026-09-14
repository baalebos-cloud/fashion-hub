/**
 * Token persistence, isolated to this one file so the storage mechanism
 * (currently sessionStorage) can change without touching the interceptor,
 * stores, or hooks that call these functions.
 *
 * sessionStorage (not localStorage) is used deliberately: it clears when
 * the tab closes, limiting the blast radius of an XSS-exfiltrated token
 * compared to a token that persists indefinitely across browser restarts.
 */
const ACCESS_TOKEN_KEY = "fashionhub.access_token";
const REFRESH_TOKEN_KEY = "fashionhub.refresh_token";

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens({ accessToken, refreshToken }: TokenPair): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function hasSession(): boolean {
  return getAccessToken() !== null;
}
