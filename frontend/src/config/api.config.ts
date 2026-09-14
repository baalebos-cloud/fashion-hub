import { env } from "./environment";

/**
 * Base API configuration consumed by lib/api/client.ts. Endpoint paths
 * themselves live in lib/api/endpoints.ts, not here — this file only
 * covers connection-level concerns.
 */
export const apiConfig = {
  baseUrl: env.apiBaseUrl,
  timeoutMs: 15_000,
  withCredentials: false, // bearer-token auth, not cookie-based sessions
} as const;
