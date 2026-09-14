/**
 * Typed access to Vite env vars (import.meta.env.*). Every other config
 * file reads through here rather than touching import.meta.env directly,
 * so a missing/misnamed env var fails fast with a clear message instead
 * of silently becoming `undefined` deep in a component.
 */
function readEnv(key: string, fallback?: string): string {
  const value = import.meta.env[key] as string | undefined;
  if (value === undefined || value === "") {
    if (fallback !== undefined) return fallback;
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

function readBoolEnv(key: string, fallback: boolean): boolean {
  const raw = import.meta.env[key] as string | undefined;
  if (raw === undefined) return fallback;
  return raw === "true";
}

export const env = {
  apiBaseUrl: readEnv("VITE_API_BASE_URL", "/api/v1"),
  appName: readEnv("VITE_APP_NAME", "Fashion Hub"),
  appEnv: readEnv("VITE_APP_ENV", "development") as "development" | "staging" | "production",
  isProduction: readEnv("VITE_APP_ENV", "development") === "production",

  mapsProvider: readEnv("VITE_MAPS_PROVIDER", "google_maps"),
  mapsPublicKey: readEnv("VITE_MAPS_PUBLIC_KEY", ""),

  paymentProvider: readEnv("VITE_PAYMENT_PROVIDER", "paystack"),
  paymentPublicKey: readEnv("VITE_PAYMENT_PUBLIC_KEY", ""),

  enableAIAssistant: readBoolEnv("VITE_ENABLE_AI_ASSISTANT", true),
  enableMessaging: readBoolEnv("VITE_ENABLE_MESSAGING", true),
};
