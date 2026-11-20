import { env } from "./environment";

/** Application-wide, non-secret constants. */
export const appConfig = {
  name: env.appName,
  defaultLocale: "en-US",
  defaultCurrency: "NGN",
  defaultTimezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  /** Empty until VITE_SUPPORT_EMAIL is set: pages then hide the email link rather than show a fake one. */
  supportEmail: env.supportEmail,
  pagination: {
    defaultPageSize: 20,
    maxPageSize: 100,
  },
} as const;
