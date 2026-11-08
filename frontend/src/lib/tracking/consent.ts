/**
 * Whether this browser asked not to be tracked: Global Privacy Control, Do Not Track, or the
 * "Stop on this browser" button on the Privacy page. Kept free of imports so the API client can
 * use it to tell the server on every request (X-Tracking-Consent: off), signed in or not.
 */
export const OPT_OUT_KEY = "tailora.recs_opt_out";

export function trackingDisabled(): boolean {
  const nav = globalThis.navigator as (Navigator & { globalPrivacyControl?: boolean }) | undefined;
  if (nav?.globalPrivacyControl === true || nav?.doNotTrack === "1") return true;
  try {
    return globalThis.localStorage?.getItem(OPT_OUT_KEY) === "1";
  } catch {
    return false;
  }
}
